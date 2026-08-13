from __future__ import annotations

import argparse
import base64
import contextlib
import io
import traceback
from pathlib import Path
from typing import Any

import matplotlib
import nbformat
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _display_payload(value: Any) -> dict[str, str]:
    payload = {"text/plain": repr(value)}
    if isinstance(value, pd.DataFrame):
        payload["text/html"] = value.to_html(max_rows=30, max_cols=20, border=0)
    elif isinstance(value, pd.Series):
        payload["text/html"] = value.to_frame().to_html(max_rows=30, border=0)
    return payload


def execute_notebook(path: Path) -> None:
    notebook = nbformat.read(path, as_version=4)
    namespace: dict[str, Any] = {"__name__": "__main__"}
    execution_count = 0
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        execution_count += 1
        outputs: list[dict[str, Any]] = []

        def display(
            *values: Any, _outputs: list[dict[str, Any]] = outputs
        ) -> None:
            for value in values:
                _outputs.append(
                    nbformat.v4.new_output("display_data", data=_display_payload(value), metadata={})
                )

        namespace["display"] = display
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(compile(cell.source, f"{path.name}:cell-{execution_count}", "exec"), namespace)
        except Exception as exc:
            outputs.append(
                nbformat.v4.new_output(
                    "error",
                    ename=type(exc).__name__,
                    evalue=str(exc),
                    traceback=traceback.format_exc().splitlines(),
                )
            )
            cell.execution_count = execution_count
            cell.outputs = outputs
            nbformat.write(notebook, path)
            raise
        if stdout.getvalue():
            outputs.append(nbformat.v4.new_output("stream", name="stdout", text=stdout.getvalue()))
        if stderr.getvalue():
            outputs.append(nbformat.v4.new_output("stream", name="stderr", text=stderr.getvalue()))
        for figure_number in plt.get_fignums():
            figure = plt.figure(figure_number)
            buffer = io.BytesIO()
            figure.savefig(buffer, format="png", dpi=130, bbox_inches="tight")
            outputs.append(
                nbformat.v4.new_output(
                    "display_data",
                    data={"image/png": base64.b64encode(buffer.getvalue()).decode("ascii")},
                    metadata={},
                )
            )
        plt.close("all")
        cell.execution_count = execution_count
        cell.outputs = outputs
    notebook.metadata["execution"] = {
        "engine": "trusted in-process runner",
        "reason": "portable fallback for environments where Jupyter kernel sockets are unavailable",
        "status": "completed",
    }
    nbformat.write(notebook, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a trusted project notebook in-process")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    execute_notebook(args.path)
    print(args.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
