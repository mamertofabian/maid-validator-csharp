"""Behavioral contract for C#-aware type comparison."""

from __future__ import annotations

from pathlib import Path

import pytest

from maid_runner.core.result import ErrorCode
from maid_runner.core.types import ArtifactKind, ValidationMode
from maid_runner.core.validate import ValidationEngine
from maid_runner.validators.base import BaseValidator

from maid_validator_csharp.validator import CSharpValidator


@pytest.mark.parametrize(
    "manifest_type,implementation_type",
    [
        ("bool", "System.Boolean"),
        ("byte", "System.Byte"),
        ("sbyte", "System.SByte"),
        ("char", "System.Char"),
        ("decimal", "System.Decimal"),
        ("double", "System.Double"),
        ("float", "System.Single"),
        ("int", "System.Int32"),
        ("uint", "System.UInt32"),
        ("long", "System.Int64"),
        ("ulong", "System.UInt64"),
        ("short", "System.Int16"),
        ("ushort", "System.UInt16"),
        ("object", "System.Object"),
        ("string", "global::System.String"),
        ("global::Alpha.Widget", "Alpha.Widget"),
        ("void", "System.Void"),
        ("dynamic", "System.Object"),
        ("nint", "System.IntPtr"),
        ("nuint", "System.UIntPtr"),
        ("int?", "System.Nullable<System.Int32>"),
        ("string?", "System.String"),
        ("object?", "System.Object"),
        ("int[]?", "System.Int32[]"),
        ("int[]", "System.Int32 []"),
        ("int[,]", "System.Int32[ , ]"),
        (
            "Dictionary<string, List<int?>>",
            "System.Collections.Generic.Dictionary<System.String, "
            "System.Collections.Generic.List<System.Nullable<System.Int32>>>",
        ),
        ("(int Id, string Name)", "(System.Int32, System.String)"),
        (
            "Task<(int id, string? name)[]>",
            "System.Threading.Tasks.Task<(System.Int32, System.String)[]>",
        ),
    ],
)
def test_equivalent_csharp_type_spellings_match(
    manifest_type: str,
    implementation_type: str,
) -> None:
    validator = CSharpValidator()

    assert validator.types_match(manifest_type, implementation_type) is True


@pytest.mark.parametrize(
    "manifest_type,implementation_type",
    [
        ("int", "long"),
        ("int", "int?"),
        ("Widget", "Widget?"),
        ("Widget", "Alpha.Widget"),
        ("Alpha.Widget", "Beta.Widget"),
        ("Custom.List<int>", "System.Collections.Generic.List<System.Int32>"),
        (
            "delegate* unmanaged[Cdecl]<ref int, Widget>",
            "delegate* unmanaged[Cdecl]<refSystem.Int32, Widget>",
        ),
        ("List<int>", "List<string>"),
        ("int[]", "int[,]"),
        ("int[][,]", "int[,][]"),
        ("(int, string)", "(string, int)"),
        ("(int, string)", "(int, string, bool)"),
    ],
)
def test_distinct_csharp_type_spellings_do_not_match(
    manifest_type: str,
    implementation_type: str,
) -> None:
    validator = CSharpValidator()

    assert validator.types_match(manifest_type, implementation_type) is False


def test_unspecified_manifest_type_preserves_runner_semantics() -> None:
    try:
        from maid_validator_csharp._types import csharp_types_match
    except ModuleNotFoundError:
        pytest.fail("C# type comparison module is not implemented")

    assert csharp_types_match(None, "System.Int32") is True
    assert csharp_types_match(None, None) is True
    assert csharp_types_match("int", None) is False
    assert csharp_types_match("", "") is True


@pytest.mark.parametrize(
    "spaced,compact",
    [
        ("int *", "System.Int32*"),
        (
            "delegate * unmanaged [ Cdecl ] < int , void >",
            "delegate* unmanaged[Cdecl]<System.Int32,System.Void>",
        ),
    ],
)
def test_unsupported_csharp_type_syntax_is_deterministic_and_non_crashing(
    spaced: str,
    compact: str,
) -> None:
    try:
        from maid_validator_csharp._types import (
            csharp_types_match,
            normalize_csharp_type,
        )
    except ModuleNotFoundError:
        pytest.fail("C# type comparison module is not implemented")

    first = normalize_csharp_type(spaced)
    second = normalize_csharp_type(spaced)

    assert first == second
    assert csharp_types_match(spaced, compact) is True


def test_collected_and_snapshot_type_spellings_remain_raw() -> None:
    source = (
        "public class Converter\n"
        "{\n"
        "    public System.Threading.Tasks.Task<"
        "System.Collections.Generic.List<System.Nullable<System.Int32>>> "
        "Convert(System.Int32[] values) { return null; }\n"
        "}\n"
    )
    validator = CSharpValidator()

    collected = validator.collect_implementation_artifacts(source, "Converter.cs")
    method = next(
        artifact
        for artifact in collected.artifacts
        if artifact.kind == ArtifactKind.METHOD and artifact.name == "Convert"
    )
    snapshot_method = next(
        artifact
        for artifact in validator.generate_snapshot(source, "Converter.cs")
        if artifact["kind"] == "method" and artifact["name"] == "Convert"
    )

    assert method.args[0].type == "System.Int32[]"
    assert method.returns == (
        "System.Threading.Tasks.Task<"
        "System.Collections.Generic.List<System.Nullable<System.Int32>>>"
    )
    assert snapshot_method["args"][0]["type"] == "System.Int32[]"
    assert snapshot_method["returns"] == method.returns


def test_validation_engine_accepts_nested_csharp_alias_equivalence(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifests" / "type-equivalence.manifest.yaml"
    manifest_path.parent.mkdir()
    manifest_path.write_text("""\
schema: "2"
goal: "Validate equivalent C# type spellings"
files:
  edit:
    - path: src/Converter.cs
      artifacts:
        - kind: class
          name: Converter
        - kind: method
          name: Convert
          of: Converter
          args:
            - name: values
              type: int[]
          returns: Task<List<int?>>
  read:
    - tests/ConverterTests.cs
validate:
  - [dotnet, test]
""")
    source_path = tmp_path / "src" / "Converter.cs"
    source_path.parent.mkdir()
    source_path.write_text(
        "public class Converter {\n"
        "  public System.Threading.Tasks.Task<"
        "System.Collections.Generic.List<System.Nullable<System.Int32>>> "
        "Convert(System.Int32[] values) { return null; }\n"
        "}\n"
    )
    test_path = tmp_path / "tests" / "ConverterTests.cs"
    test_path.parent.mkdir()
    test_path.write_text(
        "public class ConverterTests {\n"
        "  [Fact] public void Converts() {\n"
        "    var converter = new Converter();\n"
        "    converter.Convert(new int[0]);\n"
        "  }\n"
        "}\n"
    )

    result = ValidationEngine(project_root=tmp_path).validate(
        manifest_path,
        mode=ValidationMode.IMPLEMENTATION,
    )

    assert not any(error.code == ErrorCode.TYPE_MISMATCH for error in result.errors)
    assert result.success is True


def test_missing_runner_type_hook_fails_visibly(monkeypatch) -> None:
    monkeypatch.delattr(BaseValidator, "types_match", raising=False)

    with pytest.raises(ImportError, match="BaseValidator.types_match"):
        CSharpValidator()
