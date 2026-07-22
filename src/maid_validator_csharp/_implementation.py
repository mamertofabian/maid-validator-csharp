"""Collect C# artifact DEFINITIONS (the public API surface) from source.

Maps C# constructs onto MAID's language-neutral ``ArtifactKind`` vocabulary:

    namespace                         -> NAMESPACE
    class / struct / record           -> CLASS
    interface                         -> INTERFACE
    enum                              -> ENUM
    delegate                          -> TYPE
    method / constructor              -> METHOD (of = declaring type)
    property / field                  -> ATTRIBUTE (of = declaring type)
    top-level local function          -> FUNCTION

Only the public API surface is emitted: ``public``/``protected`` members and
``public`` types, plus interface members (implicitly public) and top-level
local functions. ``private``/``internal``/implicitly-private members are
dropped. Leading-underscore names remain private via ``FoundArtifact``.
"""

from __future__ import annotations

from typing import Any, Optional

from maid_runner.core.types import ArgSpec, ArtifactKind
from maid_runner.validators.base import FoundArtifact

_TYPE_DECLARATIONS = {
    "class_declaration": ArtifactKind.CLASS,
    "struct_declaration": ArtifactKind.CLASS,
    "record_declaration": ArtifactKind.CLASS,
    "record_struct_declaration": ArtifactKind.CLASS,
    "interface_declaration": ArtifactKind.INTERFACE,
    "enum_declaration": ArtifactKind.ENUM,
}

_STRUCTURAL = {"compilation_unit", "global_statement", "declaration_list"}


def collect_implementation_artifacts(root: Any, source: bytes) -> list[FoundArtifact]:
    artifacts: list[FoundArtifact] = []
    _visit(root, source, artifacts, current_type=None, in_interface=False)
    return artifacts


def _visit(
    node: Any,
    source: bytes,
    artifacts: list[FoundArtifact],
    current_type: Optional[str],
    in_interface: bool,
) -> None:
    node_type = node.type

    if node_type in _STRUCTURAL:
        for child in node.children:
            _visit(child, source, artifacts, current_type, in_interface)
        return

    if node_type in ("namespace_declaration", "file_scoped_namespace_declaration"):
        name = _text(_field(node, "name"), source)
        if name:
            artifacts.append(
                FoundArtifact(kind=ArtifactKind.NAMESPACE, name=name, line=_line(node))
            )
        body = _field(node, "body")
        if body is not None:
            for child in body.children:
                _visit(child, source, artifacts, None, False)
        return

    if node_type in _TYPE_DECLARATIONS:
        _collect_type_declaration(node, source, artifacts)
        return

    if node_type == "delegate_declaration":
        if _is_public_type(node):
            args, returns = _signature(node, source, returns_field="type")
            artifacts.append(
                FoundArtifact(
                    kind=ArtifactKind.TYPE,
                    name=_text(_field(node, "name"), source),
                    args=args,
                    returns=returns,
                    type_parameters=_type_parameters(node, source),
                    line=_line(node),
                )
            )
        return

    if node_type in ("method_declaration", "constructor_declaration"):
        _collect_method(node, source, artifacts, current_type, in_interface)
        return

    if node_type == "property_declaration":
        if _is_visible_member(node, in_interface):
            artifacts.append(
                FoundArtifact(
                    kind=ArtifactKind.ATTRIBUTE,
                    name=_text(_field(node, "name"), source),
                    of=current_type,
                    type_annotation=_type_text(_field(node, "type"), source),
                    line=_line(node),
                )
            )
        return

    if node_type in ("field_declaration", "event_field_declaration"):
        if _is_visible_member(node, in_interface):
            _collect_field(node, source, artifacts, current_type)
        return

    if node_type == "local_function_statement":
        # Only top-level local functions are reachable here (method bodies are
        # never recursed), so every one is a namespace-free FUNCTION.
        args, returns = _signature(node, source, returns_field="type")
        artifacts.append(
            FoundArtifact(
                kind=ArtifactKind.FUNCTION,
                name=_text(_field(node, "name"), source),
                args=args,
                returns=returns,
                type_parameters=_type_parameters(node, source),
                is_async=_is_async(node),
                line=_line(node),
            )
        )
        return


def _collect_type_declaration(
    node: Any, source: bytes, artifacts: list[FoundArtifact]
) -> None:
    if not _is_public_type(node):
        return
    name = _text(_field(node, "name"), source)
    kind = _TYPE_DECLARATIONS[node.type]
    in_interface = node.type == "interface_declaration"
    artifacts.append(
        FoundArtifact(
            kind=kind,
            name=name,
            bases=_bases(node, source),
            type_parameters=_type_parameters(node, source),
            line=_line(node),
        )
    )

    # Positional record parameters are public properties.
    if node.type in ("record_declaration", "record_struct_declaration"):
        params = _first_child_of_type(node, "parameter_list")
        if params is not None:
            for arg in _parameters(params, source):
                artifacts.append(
                    FoundArtifact(
                        kind=ArtifactKind.ATTRIBUTE,
                        name=arg.name,
                        of=name,
                        type_annotation=arg.type,
                        line=_line(node),
                    )
                )

    body = _field(node, "body")
    if body is not None:
        for child in body.children:
            _visit(child, source, artifacts, name, in_interface)


def _collect_method(
    node: Any,
    source: bytes,
    artifacts: list[FoundArtifact],
    current_type: Optional[str],
    in_interface: bool,
) -> None:
    if not _is_visible_member(node, in_interface):
        return
    is_constructor = node.type == "constructor_declaration"
    args, returns = _signature(
        node, source, returns_field=None if is_constructor else "returns"
    )
    artifacts.append(
        FoundArtifact(
            kind=ArtifactKind.METHOD,
            name=_text(_field(node, "name"), source),
            of=current_type,
            args=args,
            returns=returns,
            is_async=_is_async(node),
            type_parameters=_type_parameters(node, source),
            line=_line(node),
        )
    )


def _collect_field(
    node: Any,
    source: bytes,
    artifacts: list[FoundArtifact],
    current_type: Optional[str],
) -> None:
    declaration = _first_child_of_type(node, "variable_declaration")
    if declaration is None:
        return
    type_text = _type_text(_field(declaration, "type"), source)
    for child in declaration.children:
        if child.type != "variable_declarator":
            continue
        name_node = _field(child, "name")
        if name_node is None:
            continue
        artifacts.append(
            FoundArtifact(
                kind=ArtifactKind.ATTRIBUTE,
                name=_text(name_node, source),
                of=current_type,
                type_annotation=type_text,
                line=_line(node),
            )
        )


# --- signature / type helpers -------------------------------------------------


def _signature(
    node: Any, source: bytes, returns_field: Optional[str]
) -> tuple[tuple[ArgSpec, ...], Optional[str]]:
    params = _field(node, "parameters")
    args = _parameters(params, source) if params is not None else ()
    returns = None
    if returns_field is not None:
        returns = _type_text(_field(node, returns_field), source)
    return args, returns


def _parameters(params: Any, source: bytes) -> tuple[ArgSpec, ...]:
    args: list[ArgSpec] = []
    for child in params.children:
        if child.type != "parameter":
            continue
        name_node = _field(child, "name")
        if name_node is None:
            continue
        args.append(
            ArgSpec(
                name=_text(name_node, source),
                type=_type_text(_field(child, "type"), source),
                default=_default_value(child, source),
            )
        )
    return tuple(args)


def _default_value(param: Any, source: bytes) -> Optional[str]:
    for child in param.children:
        if child.type == "=":
            text = source[child.end_byte : param.end_byte].decode("utf-8").strip()
            return text or None
    return None


def _bases(node: Any, source: bytes) -> tuple[str, ...]:
    base_list = _first_child_of_type(node, "base_list")
    if base_list is None:
        return ()
    return tuple(_text(child, source) for child in base_list.children if child.is_named)


def _type_parameters(node: Any, source: bytes) -> tuple[str, ...]:
    tp_list = _field(node, "type_parameters") or _first_child_of_type(
        node, "type_parameter_list"
    )
    if tp_list is None:
        return ()
    names: list[str] = []
    for child in tp_list.children:
        if child.type != "type_parameter":
            continue
        name_node = _field(child, "name") or child
        names.append(_text(name_node, source))
    return tuple(names)


def _type_text(node: Any, source: bytes) -> Optional[str]:
    if node is None:
        return None
    text = _text(node, source).strip()
    return text or None


# --- visibility ---------------------------------------------------------------


def _modifiers(node: Any) -> set[str]:
    return {
        child.text.decode("utf-8")
        for child in node.children
        if child.type == "modifier"
    }


def _is_public_type(node: Any) -> bool:
    return "public" in _modifiers(node)


def _is_visible_member(node: Any, in_interface: bool) -> bool:
    mods = _modifiers(node)
    if "private" in mods:
        return False
    if in_interface:
        return True
    # Explicit interface implementations (e.g. `Task IFoo.Bar()`) carry no
    # access modifier — C# forbids one — but are part of the public contract.
    if _first_child_of_type(node, "explicit_interface_specifier") is not None:
        return True
    return "public" in mods or "protected" in mods


def _is_async(node: Any) -> bool:
    return "async" in _modifiers(node)


# --- node utilities -----------------------------------------------------------


def _field(node: Any, name: str) -> Any:
    return node.child_by_field_name(name)


def _first_child_of_type(node: Any, type_name: str) -> Any:
    for child in node.children:
        if child.type == type_name:
            return child
    return None


def _text(node: Any, source: bytes) -> str:
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _line(node: Any) -> int:
    return node.start_point[0] + 1
