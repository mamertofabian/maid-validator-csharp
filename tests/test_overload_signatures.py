"""Behavioral contract for exact C# definition overload signatures."""

from __future__ import annotations

import pytest
from tree_sitter import Language, Parser
import tree_sitter_c_sharp

from maid_runner.core._implementation_validation import compare_artifacts
from maid_runner.core.types import ArtifactKind, ArtifactSpec
from maid_runner.validators.base import FoundArtifact

from maid_validator_csharp import CSharpValidator
from maid_validator_csharp._implementation import collect_implementation_artifacts
from maid_validator_csharp._parse import parse_csharp_source

PARSER = Parser(Language(tree_sitter_c_sharp.language()))


@pytest.fixture
def validator() -> CSharpValidator:
    return CSharpValidator()


def _implementation(
    _validator: CSharpValidator,
    source: str,
) -> list[FoundArtifact]:
    session = parse_csharp_source(source, PARSER)
    assert session.parse_errors == []
    return collect_implementation_artifacts(
        session.tree.root_node,
        session.source_bytes,
    )


def _behavioral(validator: CSharpValidator, source: str) -> list[FoundArtifact]:
    result = validator.collect_behavioral_artifacts(source, "OverloadTests.cs")
    assert result.errors == []
    return list(result.artifacts)


def _callables(artifacts: list[FoundArtifact]) -> list[FoundArtifact]:
    return [
        artifact
        for artifact in artifacts
        if artifact.kind in {ArtifactKind.FUNCTION, ArtifactKind.METHOD}
    ]


def test_overloaded_definitions_emit_distinct_canonical_signatures(validator) -> None:
    artifacts = _implementation(
        validator,
        """
public class Converter
{
    public int Convert(int value) => value;
    public string Convert(string value) => value;
}
""",
    )

    overloads = [
        artifact for artifact in _callables(artifacts) if artifact.name == "Convert"
    ]
    assert [artifact.signature for artifact in overloads] == [
        "Convert(System.Int32)",
        "Convert(System.String)",
    ]
    assert [artifact.args[0].type for artifact in overloads] == ["int", "string"]
    assert [artifact.returns for artifact in overloads] == ["int", "string"]
    assert overloads[0].contract_key() != overloads[1].contract_key()


def test_signature_uses_generic_arity_and_by_reference_identity(validator) -> None:
    artifacts = _implementation(
        validator,
        """
public class Mapper
{
    public T Map<T>(T item) => item;
    public int Parse(int value = 0) => value;
    public int Parse(ref int other) => other;
    public void Read(in int value) { }
    public void Write(out int value) { value = 0; }
}
""",
    )

    signatures = {artifact.signature for artifact in _callables(artifacts)}
    assert "Map``1(T)" in signatures
    assert "Parse(System.Int32)" in signatures
    assert "Parse(ref System.Int32)" in signatures
    assert "Read(ref System.Int32)" in signatures
    assert "Write(ref System.Int32)" in signatures
    assert all("value" not in signature for signature in signatures if signature)
    assert all("= 0" not in signature for signature in signatures if signature)


def test_params_constructors_and_top_level_functions_keep_parameter_types(
    validator,
) -> None:
    artifacts = _implementation(
        validator,
        """
public class Collector
{
    public Collector(int capacity) { }
    public void Collect(params object[] values) { }
}
int Add(int left, int right) => left + right;
""",
    )

    signatures = {artifact.signature for artifact in _callables(artifacts)}
    assert "Collector(System.Int32)" in signatures
    assert "Collect(System.Object[])" in signatures
    assert "Add(System.Int32,System.Int32)" in signatures
    collect = next(artifact for artifact in artifacts if artifact.name == "Collect")
    assert [(arg.name, arg.type) for arg in collect.args] == [("values", "object[]")]


def test_explicit_interface_definitions_keep_interface_identity(validator) -> None:
    artifacts = _implementation(
        validator,
        """
public interface IFoo { void Render(int value); }
public interface IBar { void Render(int value); }
public class Renderer : IFoo, IBar
{
    void IFoo.Render(int value) { }
    void IBar.Render(int value) { }
}
""",
    )

    definitions = [
        artifact
        for artifact in artifacts
        if artifact.kind == ArtifactKind.METHOD
        and artifact.name == "Render"
        and artifact.of == "Renderer"
    ]
    assert [artifact.signature for artifact in definitions] == [
        "IFoo.Render(System.Int32)",
        "IBar.Render(System.Int32)",
    ]
    assert all(artifact.name == "Render" for artifact in definitions)
    assert len({artifact.contract_key() for artifact in definitions}) == 2

    expected = [
        ArtifactSpec(
            kind=ArtifactKind.METHOD,
            name="Render",
            of="Renderer",
            signature=signature,
        )
        for signature in (
            "IFoo.Render(System.Int32)",
            "IBar.Render(System.Int32)",
        )
    ]
    assert compare_artifacts(expected, artifacts, "Renderer.cs", False) == []


def test_arglist_is_distinct_from_an_empty_parameter_list(validator) -> None:
    artifacts = _implementation(
        validator,
        """
public class Variadic
{
    public void Invoke() { }
    public void Invoke(__arglist) { }
}
""",
    )

    overloads = [
        artifact
        for artifact in artifacts
        if artifact.kind == ArtifactKind.METHOD and artifact.name == "Invoke"
    ]
    assert [artifact.signature for artifact in overloads] == [
        "Invoke()",
        "Invoke(__arglist)",
    ]
    assert [arg.name for arg in overloads[1].args] == ["__arglist"]
    assert len({artifact.contract_key() for artifact in overloads}) == 2


def test_exact_runner_matching_selects_the_requested_csharp_overload(validator) -> None:
    found = _implementation(
        validator,
        """
public class Converter
{
    public int Convert(int value) => value;
    public string Convert(string value) => value;
}
""",
    )

    expected = ArtifactSpec(
        kind=ArtifactKind.METHOD,
        name="Convert",
        of="Converter",
        returns="int",
        signature="Convert(System.Int32)",
    )
    assert compare_artifacts([expected], found, "Converter.cs", False) == []

    missing = ArtifactSpec(
        kind=ArtifactKind.METHOD,
        name="Convert",
        of="Converter",
        signature="Convert(System.Boolean)",
    )
    errors = compare_artifacts([missing], found, "Converter.cs", False)
    assert len(errors) == 1
    assert errors[0].code.value == "E300"


def test_syntax_only_behavioral_references_never_guess_signatures(validator) -> None:
    references = _behavioral(
        validator,
        """
using Xunit;
public class OverloadTests
{
    [Fact]
    public void Calls()
    {
        Converter.Convert(1);
        var converter = new Converter();
        converter.Convert("value");
        Render(1);
        _ = nameof(Converter.Convert);
    }
}
""",
    )

    call_references = _callables(references)
    assert call_references
    assert all(reference.signature is None for reference in call_references)
