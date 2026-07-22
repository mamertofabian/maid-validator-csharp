"""Behavioral coverage for C# namespace identities."""

from pathlib import Path

from maid_runner.core.result import ErrorCode
from maid_runner.core.types import ArtifactKind, ValidationMode
from maid_runner.core.validate import ValidationEngine

from maid_validator_csharp import CSharpValidator


def test_using_directive_collects_exact_namespace_reference() -> None:
    result = CSharpValidator().collect_behavioral_artifacts(
        "using Example.Services;\n",
        "WidgetTests.cs",
    )

    assert result.errors == []
    assert any(
        artifact.kind == ArtifactKind.NAMESPACE and artifact.name == "Example.Services"
        for artifact in result.artifacts
    )


def test_static_using_does_not_claim_namespace_coverage() -> None:
    result = CSharpValidator().collect_behavioral_artifacts(
        "using static Example.Widget;\n",
        "WidgetTests.cs",
    )

    assert result.errors == []
    assert not any(
        artifact.kind == ArtifactKind.NAMESPACE for artifact in result.artifacts
    )


def test_type_alias_using_does_not_claim_namespace_coverage() -> None:
    result = CSharpValidator().collect_behavioral_artifacts(
        "using WidgetAlias = Example.Services.Widget;\n",
        "WidgetTests.cs",
    )

    assert result.errors == []
    assert not any(
        artifact.kind == ArtifactKind.NAMESPACE for artifact in result.artifacts
    )


def test_namespace_and_contained_class_satisfy_end_to_end_validation(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifests" / "namespace-coverage.manifest.yaml"
    manifest_path.parent.mkdir()
    manifest_path.write_text("""schema: "2"
goal: Validate a C# namespace and its contained class
type: fix
files:
  edit:
    - path: src/Widget.cs
      artifacts:
        - kind: namespace
          name: Example.Services
        - kind: class
          name: Widget
  read:
    - tests/WidgetTests.cs
validate:
  - [dotnet, test]
""")
    source_path = tmp_path / "src" / "Widget.cs"
    source_path.parent.mkdir()
    source_path.write_text("namespace Example.Services;\npublic class Widget { }\n")
    test_path = tmp_path / "tests" / "WidgetTests.cs"
    test_path.parent.mkdir()
    test_path.write_text(
        "using Example.Services;\n"
        "public class WidgetTests {\n"
        "  [Fact] public void CreatesWidget() { var widget = new Widget(); }\n"
        "}\n"
    )

    result = ValidationEngine(project_root=tmp_path).validate(
        manifest_path,
        mode=ValidationMode.IMPLEMENTATION,
    )

    assert not any(
        error.code == ErrorCode.ARTIFACT_NOT_USED_IN_TESTS for error in result.errors
    )
    assert result.success is True
