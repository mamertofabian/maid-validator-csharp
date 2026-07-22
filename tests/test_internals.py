"""Direct unit tests for the internal seams behind CSharpValidator.

These exercise the module-level collectors and the parse session directly (by
their own module identity), rather than only through the public validator, so
each internal artifact has focused behavioral coverage.
"""

from __future__ import annotations

import pytest

from maid_runner.core.types import ArtifactKind

from maid_validator_csharp._behavioral import collect_behavioral_artifacts
from maid_validator_csharp._implementation import collect_implementation_artifacts
from maid_validator_csharp._parse import (
    CSharpParseSession,
    collect_parse_errors,
    parse_csharp_source,
)
from maid_validator_csharp.validator import CSharpValidator


@pytest.fixture
def parser():
    return CSharpValidator()._parser


def test_parse_csharp_source_returns_session_with_bytes_and_tree(parser):
    session = parse_csharp_source("public class C { }\n", parser)
    assert isinstance(session, CSharpParseSession)
    assert session.source_bytes == b"public class C { }\n"
    assert session.tree.root_node.type == "compilation_unit"
    assert session.parse_errors == []


def test_parse_csharp_source_reports_syntax_errors(parser):
    session = parse_csharp_source("public class {\n", parser)
    assert session.parse_errors


def test_collect_parse_errors_flags_error_nodes(parser):
    session = parse_csharp_source("public class {\n", parser)
    errors = collect_parse_errors(session.tree.root_node)
    assert isinstance(errors, list)
    assert errors


def test_collect_parse_errors_clean_source_has_no_errors(parser):
    session = parse_csharp_source("public class C { }\n", parser)
    assert collect_parse_errors(session.tree.root_node) == []


def test_collect_implementation_artifacts_module_fn_extracts_class(parser):
    session = parse_csharp_source(
        "public class Widget { public void Draw() {} }\n", parser
    )
    artifacts = collect_implementation_artifacts(
        session.tree.root_node, session.source_bytes
    )
    kinds = {(a.kind, a.name, a.of) for a in artifacts}
    assert (ArtifactKind.CLASS, "Widget", None) in kinds
    assert (ArtifactKind.METHOD, "Draw", "Widget") in kinds


def test_collect_behavioral_artifacts_module_fn_extracts_reference(parser):
    source = (
        "using Xunit;\n"
        "public class T { [Fact] public void M() { var w = new Widget(); } }\n"
    )
    session = parse_csharp_source(source, parser)
    artifacts = collect_behavioral_artifacts(
        session.tree.root_node, session.source_bytes
    )
    assert any(a.kind == ArtifactKind.CLASS and a.name == "Widget" for a in artifacts)
    assert any(
        a.kind == ArtifactKind.TEST_FUNCTION and a.name == "M" for a in artifacts
    )


def test_csharp_validator_class_from_validator_module():
    validator = CSharpValidator()
    assert validator.supported_extensions() == (".cs",)
