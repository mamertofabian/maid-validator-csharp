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
    bindings = _collect_local_bindings(root, source, artifacts)
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
                _collect_initializer_attributes(node, name, source, artifacts)
        elif node_type == "implicit_object_creation_expression":
            owner = _enclosing_declared_type(node, source)
            if owner:
                _collect_initializer_attributes(node, owner, source, artifacts)
        elif node_type == "invocation_expression":
            _collect_invocation(node, source, artifacts, bindings)
        elif node_type == "typeof_expression":
            _collect_type_reference(_field(node, "type"), source, artifacts, node)

        stack.extend(reversed(node.children))

    return artifacts


def _collect_invocation(
    node: Any,
    source: bytes,
    artifacts: list[FoundArtifact],
    bindings: list[tuple[Any, str, set[str]]],
) -> None:
    function = _field(node, "function")
    if function is None:
        return
    if function.type == "identifier":
        if _text(function, source) == "nameof":
            _collect_nameof_reference(node, source, artifacts)
            return
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
        receiver_name = (
            _text(receiver, source)
            if receiver is not None and receiver.type == "identifier"
            else ""
        )
        owners = _visible_binding_owners(node, receiver_name, bindings)
        for owner in owners:
            artifacts.append(
                FoundArtifact(
                    kind=ArtifactKind.METHOD,
                    name=_text(name_node, source),
                    of=owner,
                    line=_line(node),
                )
            )


def _collect_nameof_reference(
    node: Any, source: bytes, artifacts: list[FoundArtifact]
) -> None:
    stack = list(node.children)
    candidates: list[Any] = []
    while stack:
        child = stack.pop()
        if child.type == "member_access_expression":
            candidates.append(child)
        stack.extend(child.children)
    if not candidates:
        return
    member = max(
        candidates, key=lambda candidate: candidate.end_byte - candidate.start_byte
    )
    owner = _member_owner_name(_field(member, "expression"), source)
    name = _field(member, "name")
    if owner and name is not None:
        artifacts.append(
            FoundArtifact(
                kind=ArtifactKind.METHOD,
                name=_text(name, source),
                of=owner,
                line=_line(member),
            )
        )


def _collect_type_reference(
    type_node: Any,
    source: bytes,
    artifacts: list[FoundArtifact],
    location: Any,
) -> None:
    name = _base_type_name(type_node, source)
    if not name:
        return
    kind = ArtifactKind.INTERFACE if _looks_like_interface(name) else ArtifactKind.CLASS
    artifacts.append(FoundArtifact(kind=kind, name=name, line=_line(location)))


def _collect_local_bindings(
    root: Any, source: bytes, artifacts: list[FoundArtifact]
) -> list[tuple[Any, str, set[str]]]:
    bindings: list[tuple[Any, str, set[str]]] = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "variable_declaration":
            declared_type = _base_type_name(_field(node, "type"), source)
            if declared_type and declared_type != "var":
                kind = (
                    ArtifactKind.INTERFACE
                    if _looks_like_interface(declared_type)
                    else ArtifactKind.CLASS
                )
                artifacts.append(
                    FoundArtifact(kind=kind, name=declared_type, line=_line(node))
                )
            for child in node.children:
                if child.type != "variable_declarator":
                    continue
                variable_name = _text(_field(child, "name"), source)
                owners: set[str] = set()
                if declared_type and declared_type != "var":
                    owners.add(declared_type)
                created_type = _created_type(child, source)
                if created_type:
                    owners.add(created_type)
                bindings.append((child, variable_name, owners))
        stack.extend(reversed(node.children))
    return bindings


def _created_type(declarator: Any, source: bytes) -> str:
    for child in declarator.children:
        if child.type == "object_creation_expression":
            return _base_type_name(_field(child, "type"), source)
    return ""


def _visible_binding_owners(
    use: Any,
    name: str,
    bindings: list[tuple[Any, str, set[str]]],
) -> set[str | None]:
    candidates = [
        (declaration, owners)
        for declaration, binding_name, owners in bindings
        if binding_name == name
        and declaration.start_byte < use.start_byte
        and _node_contains(_binding_scope(declaration), use)
    ]
    if not candidates:
        return {name or None}
    _, owners = max(candidates, key=lambda candidate: candidate[0].start_byte)
    return set(owners) or {name or None}


def _binding_scope(node: Any) -> Any:
    current = node.parent
    scope_types = {
        "accessor_declaration",
        "anonymous_method_expression",
        "block",
        "constructor_declaration",
        "for_statement",
        "foreach_statement",
        "lambda_expression",
        "local_function_statement",
        "method_declaration",
        "switch_section",
        "using_statement",
    }
    while current.parent is not None and current.type not in scope_types:
        current = current.parent
    return current


def _node_contains(container: Any, node: Any) -> bool:
    return (
        container.start_byte <= node.start_byte and node.end_byte <= container.end_byte
    )


def _enclosing_declared_type(node: Any, source: bytes) -> str:
    current = node.parent
    while current is not None:
        if current.type == "variable_declaration":
            return _base_type_name(_field(current, "type"), source)
        if current.type in {"statement", "method_declaration"}:
            break
        current = current.parent
    return ""


def _collect_initializer_attributes(
    creation: Any,
    owner: str,
    source: bytes,
    artifacts: list[FoundArtifact],
) -> None:
    for child in creation.children:
        if child.type != "initializer_expression":
            continue
        for expression in child.children:
            if expression.type != "assignment_expression":
                continue
            left = _field(expression, "left")
            if left is not None and left.type == "identifier":
                artifacts.append(
                    FoundArtifact(
                        kind=ArtifactKind.ATTRIBUTE,
                        name=_text(left, source),
                        of=owner,
                        line=_line(expression),
                    )
                )


def _looks_like_interface(name: str) -> bool:
    return len(name) > 1 and name[0] == "I" and name[1].isupper()


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
        return _base_type_name(_field(type_node, "name"), source)
    if type_node.type in {
        "array_type",
        "nullable_type",
        "pointer_type",
    }:
        nested = _field(type_node, "type")
        if nested is None:
            nested = next(
                (child for child in type_node.children if child.is_named), None
            )
        return _base_type_name(nested, source)
    if type_node.type == "implicit_type":
        return "var"
    return ""


def _member_owner_name(node: Any, source: bytes) -> str:
    if node is None:
        return ""
    if node.type == "identifier":
        return _text(node, source)
    if node.type == "member_access_expression":
        return _base_type_name(_field(node, "name"), source)
    return _base_type_name(node, source)


def _field(node: Any, name: str) -> Any:
    return node.child_by_field_name(name)


def _text(node: Any, source: bytes) -> str:
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _line(node: Any) -> int:
    return node.start_point[0] + 1
