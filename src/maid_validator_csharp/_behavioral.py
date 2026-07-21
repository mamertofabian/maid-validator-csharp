"""Collect C# artifact REFERENCES from a test file.

Emits ``TEST_FUNCTION`` markers for xUnit/NUnit/MSTest test methods and
identity references for the types and methods those tests exercise:

    new Widget(...)          -> CLASS Widget
    Calc.Add(...)            -> METHOD Add (of = Calc)
    Render(...)              -> FUNCTION Render
"""

from __future__ import annotations

from typing import Any

from maid_runner.core.types import ArtifactKind
from maid_runner.validators.base import FoundArtifact

_TEST_ATTRIBUTES = {
    "Fact",
    "Theory",
    "Test",
    "TestMethod",
    "TestCase",
    "DataTestMethod",
}


def collect_behavioral_artifacts(root: Any, source: bytes) -> list[FoundArtifact]:
    artifacts: list[FoundArtifact] = []
    stack = [root]
    while stack:
        node = stack.pop()
        node_type = node.type

        if node_type == "method_declaration" and _is_test_method(node, source):
            artifacts.append(
                FoundArtifact(
                    kind=ArtifactKind.TEST_FUNCTION,
                    name=_text(_field(node, "name"), source),
                    line=_line(node),
                )
            )
        elif node_type == "object_creation_expression":
            name = _base_type_name(_field(node, "type"), source)
            if name:
                artifacts.append(
                    FoundArtifact(kind=ArtifactKind.CLASS, name=name, line=_line(node))
                )
        elif node_type == "invocation_expression":
            _collect_invocation(node, source, artifacts)

        stack.extend(reversed(node.children))

    return artifacts


def _collect_invocation(
    node: Any, source: bytes, artifacts: list[FoundArtifact]
) -> None:
    function = _field(node, "function")
    if function is None:
        return
    if function.type == "identifier":
        artifacts.append(
            FoundArtifact(
                kind=ArtifactKind.FUNCTION,
                name=_text(function, source),
                line=_line(node),
            )
        )
    elif function.type == "member_access_expression":
        name_node = _field(function, "name")
        if name_node is None:
            return
        receiver = _field(function, "expression")
        of = (
            _text(receiver, source)
            if receiver is not None and receiver.type == "identifier"
            else None
        )
        artifacts.append(
            FoundArtifact(
                kind=ArtifactKind.METHOD,
                name=_text(name_node, source),
                of=of,
                line=_line(node),
            )
        )


def _is_test_method(node: Any, source: bytes) -> bool:
    for child in node.children:
        if child.type != "attribute_list":
            continue
        for attribute in child.children:
            if attribute.type != "attribute":
                continue
            name_node = _field(attribute, "name")
            if name_node is None:
                continue
            simple = _text(name_node, source).split(".")[-1]
            if simple.endswith("Attribute"):
                simple = simple[: -len("Attribute")]
            if simple in _TEST_ATTRIBUTES:
                return True
    return False


def _base_type_name(type_node: Any, source: bytes) -> str:
    if type_node is None:
        return ""
    if type_node.type == "identifier":
        return _text(type_node, source)
    if type_node.type == "generic_name":
        for child in type_node.children:
            if child.type == "identifier":
                return _text(child, source)
    if type_node.type == "qualified_name":
        return _text(_field(type_node, "name"), source)
    return ""


def _field(node: Any, name: str) -> Any:
    return node.child_by_field_name(name)


def _text(node: Any, source: bytes) -> str:
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _line(node: Any) -> int:
    return node.start_point[0] + 1
