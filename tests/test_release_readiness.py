from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by the Python 3.10 CI job
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
RUNNER_TYPE_HOOK_COMMIT = "170545963d7c4509e6f905325b5bb79b5da513fa"


def _project_config() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_project_metadata_is_ready_for_first_pypi_release() -> None:
    project = _project_config()["project"]

    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.10"
    assert "maid-runner>=2.17,<3" in project["dependencies"]
    assert "tree-sitter>=0.25.0" in project["dependencies"]
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    assert project["urls"]["Issues"].endswith("/issues")
    assert project["urls"]["Changelog"].endswith("/blob/main/CHANGELOG.md")
    assert _project_config()["build-system"]["requires"] == [
        "setuptools==83.0.0",
        "wheel==0.47.0",
    ]
    for version in ("3.10", "3.11", "3.12", "3.13", "3.14"):
        assert f"Programming Language :: Python :: {version}" in project["classifiers"]


def test_release_uses_only_published_maid_runner_sources() -> None:
    config = _project_config()
    releasing = (ROOT / "RELEASING.md").read_text()

    assert "maid-runner>=2.17,<3" in config["project"]["dependencies"]
    assert "BaseValidator.types_match" in releasing
    assert "remove" in releasing.lower()
    assert "lower bound" in releasing.lower()


def test_development_uses_adjacent_maid_runner_source() -> None:
    config = _project_config()
    lock_text = (ROOT / "uv.lock").read_text()

    assert config["tool"]["uv"]["sources"]["maid-runner"] == {
        "path": "../maid-runner",
        "editable": True,
    }
    assert 'source = { editable = "../maid-runner" }' in lock_text


def test_release_documentation_covers_license_history_and_operator_steps() -> None:
    license_text = (ROOT / "LICENSE").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()
    releasing = (ROOT / "RELEASING.md").read_text()
    readme = (ROOT / "README.md").read_text()

    assert "MIT License" in license_text
    assert "Mamerto Fabian Jr." in license_text
    assert "## [0.1.0] - 2026-08-01" in changelog
    assert "PyPI Trusted Publisher" in releasing
    assert "maid-validator-csharp" in releasing
    assert "v0.1.0" in releasing
    assert "uv run pytest -q" in releasing
    assert "twine check" in releasing
    assert "CHANGELOG.md" in readme
    assert "RELEASING.md" in readme


def test_ci_and_publish_workflows_enforce_release_gates() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    publish = (ROOT / ".github/workflows/publish.yml").read_text()

    for version in ("3.10", "3.11", "3.12", "3.13", "3.14"):
        assert version in ci
    assert "uv sync --locked" in ci
    assert "working-directory: maid-validator-csharp" in ci
    assert "path: maid-validator-csharp" in ci
    assert "repository: mamertofabian/maid-runner" in ci
    assert f"ref: {RUNNER_TYPE_HOOK_COMMIT}" in ci
    assert "path: maid-runner" in ci
    assert "cache-dependency-glob: maid-validator-csharp/uv.lock" in ci
    assert "uv run pytest -q" in ci
    assert "uv run ruff check src/ tests/" in ci
    assert "uv run black --check src/ tests/" in ci

    assert "tags:" in publish
    assert "'v*'" in publish or '"v*"' in publish
    assert "id-token: write" in publish
    assert "name: pypi" in publish
    assert "pypa/gh-action-pypi-publish" in publish
    assert "uv build" in publish
    assert "twine check" in publish
    assert "twine==7.0.0" in publish
    assert "project.version" in publish
    assert "github.ref_name" in publish
    assert "fetch-depth: 0" in publish
    assert "merge-base --is-ancestor" in publish
    assert "origin/main" in publish
    assert "uv venv" in publish
    assert "maid validators --json" in publish
    assert "CSharpValidator" in publish
    assert "Reject development-only Runner source" in publish
    assert "[tool.uv.sources]" in publish
