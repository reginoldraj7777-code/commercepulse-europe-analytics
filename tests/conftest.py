from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from commercepulse.analysis import run_analysis
from commercepulse.config import load_profile
from commercepulse.generator import generate_scenario
from commercepulse.quality import run_quality_pipeline


@pytest.fixture(scope="session")
def built_project(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path | dict]:
    root = tmp_path_factory.mktemp("commercepulse")
    profile = replace(load_profile("ci"), customers=800, products=70, sessions=12000)
    generation = generate_scenario(profile, root / "data")
    quality = run_quality_pipeline(root / "data", root / "artifacts" / "validation")
    analysis = run_analysis(root / "data" / "clean", root / "artifacts" / "analysis")
    return {
        "root": root,
        "data": root / "data",
        "artifacts": root / "artifacts",
        "generation": generation,
        "quality": quality,
        "analysis": analysis,
    }
