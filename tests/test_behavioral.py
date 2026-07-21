"""Behavioral-collection tests: what a C# test file references."""

from __future__ import annotations

import pytest

from maid_runner.core.types import ArtifactKind
from maid_runner.validators.base import FoundArtifact

from maid_validator_csharp import CSharpValidator


@pytest.fixture
def validator() -> CSharpValidator:
    return CSharpValidator()


def _behavioral(validator: CSharpValidator, source: str) -> list[FoundArtifact]:
    result = validator.collect_behavioral_artifacts(source, "SampleTests.cs")
    assert result.errors == [], result.errors
    return list(result.artifacts)


def _has(artifacts, kind, name, of=None) -> bool:
    return any(a.kind == kind and a.name == name and a.of == of for a in artifacts)


def test_fact_and_theory_methods_become_test_functions(validator):
    source = (
        "using Xunit;\n"
        "public class WidgetTests\n"
        "{\n"
        "    [Fact]\n"
        "    public void Draws() { }\n"
        "    [Theory]\n"
        "    public void Adds(int n) { }\n"
        "    public void NotATest() { }\n"
        "}\n"
    )
    artifacts = _behavioral(validator, source)
    assert _has(artifacts, ArtifactKind.TEST_FUNCTION, "Draws")
    assert _has(artifacts, ArtifactKind.TEST_FUNCTION, "Adds")
    assert not _has(artifacts, ArtifactKind.TEST_FUNCTION, "NotATest")


def test_object_creation_is_a_class_reference(validator):
    source = (
        "using Xunit;\n"
        "public class T\n"
        "{\n"
        "    [Fact]\n"
        "    public void Creates() { var w = new Widget(); }\n"
        "}\n"
    )
    artifacts = _behavioral(validator, source)
    assert _has(artifacts, ArtifactKind.CLASS, "Widget")


def test_static_method_call_is_a_method_reference(validator):
    source = (
        "using Xunit;\n"
        "public class T\n"
        "{\n"
        "    [Fact]\n"
        "    public void Calls() { Calc.Add(1, 2); }\n"
        "}\n"
    )
    artifacts = _behavioral(validator, source)
    assert _has(artifacts, ArtifactKind.METHOD, "Add", of="Calc")


def test_free_call_is_a_function_reference(validator):
    source = (
        "using Xunit;\n"
        "public class T\n"
        "{\n"
        "    [Fact]\n"
        "    public void Calls() { Render(); }\n"
        "}\n"
    )
    artifacts = _behavioral(validator, source)
    assert _has(artifacts, ArtifactKind.FUNCTION, "Render")


def test_behavioral_parse_error_returns_errors(validator):
    result = validator.collect_behavioral_artifacts("public class {\n", "bad.cs")
    assert result.artifacts == []
    assert result.errors


def test_behavioral_empty_source(validator):
    result = validator.collect_behavioral_artifacts("", "empty.cs")
    assert result.artifacts == []
    assert result.errors == []
