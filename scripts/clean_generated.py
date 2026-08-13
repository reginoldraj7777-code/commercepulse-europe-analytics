from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "data" / "generated", ROOT / "data" / "full", ROOT / "artifacts" / "full_run_data"]


def main() -> None:
    for target in TARGETS:
        if target.parent == ROOT or ROOT in target.parents:
            shutil.rmtree(target, ignore_errors=True)
            print(f"removed {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
