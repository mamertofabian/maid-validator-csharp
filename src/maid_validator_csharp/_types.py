"""Conservative C# type canonicalization for manifest comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

_ALIASES = {
    "bool": "System.Boolean",
    "byte": "System.Byte",
    "sbyte": "System.SByte",
    "char": "System.Char",
    "decimal": "System.Decimal",
    "double": "System.Double",
    "float": "System.Single",
    "int": "System.Int32",
    "uint": "System.UInt32",
    "nint": "System.IntPtr",
    "nuint": "System.UIntPtr",
    "long": "System.Int64",
    "ulong": "System.UInt64",
    "short": "System.Int16",
    "ushort": "System.UInt16",
    "object": "System.Object",
    "string": "System.String",
    "dynamic": "System.Object",
    "void": "System.Void",
}

_WELL_KNOWN_TYPES = {
    "Dictionary": "System.Collections.Generic.Dictionary",
    "List": "System.Collections.Generic.List",
    "Nullable": "System.Nullable",
    "Task": "System.Threading.Tasks.Task",
}

_KNOWN_VALUE_TYPES = {
    "System.Boolean",
    "System.Byte",
    "System.SByte",
    "System.Char",
    "System.Decimal",
    "System.Double",
    "System.Single",
    "System.Int16",
    "System.Int32",
    "System.Int64",
    "System.UInt16",
    "System.UInt32",
    "System.UInt64",
    "System.IntPtr",
    "System.UIntPtr",
    "System.Nullable",
}

_KNOWN_REFERENCE_TYPES = {
    "System.Object",
    "System.String",
    "System.Collections.Generic.Dictionary",
    "System.Collections.Generic.List",
    "System.Threading.Tasks.Task",
}


@dataclass(frozen=True)
class _TypeNode:
    kind: str
    name: str = ""
    children: tuple[_TypeNode, ...] = ()
    rank: int = 0


class _ParseError(ValueError):
    pass


class _TokenStream:
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens
        self._position = 0

    def peek(self) -> Optional[str]:
        if self._position >= len(self._tokens):
            return None
        return self._tokens[self._position]

    def take(self) -> str:
        token = self.peek()
        if token is None:
            raise _ParseError("unexpected end of type")
        self._position += 1
        return token

    def accept(self, token: str) -> bool:
        if self.peek() != token:
            return False
        self._position += 1
        return True

    def expect(self, token: str) -> None:
        if not self.accept(token):
            raise _ParseError(f"expected {token!r}")

    def at_end(self) -> bool:
        return self.peek() is None


def normalize_csharp_type(type_str: Optional[str]) -> Optional[str]:
    """Return a stable C# type spelling for comparison only."""
    if type_str is None:
        return None

    tokens = _tokenize(type_str)
    if not tokens:
        return ""

    try:
        stream = _TokenStream(tokens)
        node = _parse_type(stream)
        if not stream.at_end():
            raise _ParseError("unsupported trailing type syntax")
        return _render(node)
    except _ParseError:
        return _fallback_normalize(tokens)


def csharp_types_match(
    manifest_type: Optional[str],
    implementation_type: Optional[str],
) -> bool:
    """Compare C# spellings while preserving Runner's missing-type semantics."""
    if manifest_type is None:
        return True
    if implementation_type is None:
        return False
    return normalize_csharp_type(manifest_type) == normalize_csharp_type(
        implementation_type
    )


def _tokenize(type_str: str) -> list[str]:
    tokens: list[str] = []
    position = 0
    while position < len(type_str):
        character = type_str[position]
        if character.isspace():
            position += 1
            continue
        if type_str.startswith("global::", position):
            tokens.append("global::")
            position += len("global::")
            continue
        if type_str.startswith("::", position):
            tokens.append("::")
            position += 2
            continue
        if character.isalpha() or character in "_@":
            end = position + 1
            while end < len(type_str):
                candidate = type_str[end]
                if not (candidate.isalnum() or candidate == "_"):
                    break
                end += 1
            tokens.append(type_str[position:end])
            position = end
            continue
        tokens.append(character)
        position += 1
    return tokens


def _parse_type(stream: _TokenStream) -> _TypeNode:
    if stream.peek() == "(":
        node = _parse_tuple(stream)
    else:
        node = _parse_named(stream)

    while True:
        if stream.accept("["):
            rank = 1
            while stream.accept(","):
                rank += 1
            stream.expect("]")
            node = _TypeNode("array", children=(node,), rank=rank)
            continue
        if stream.accept("?"):
            category = _type_category(node)
            if category == "reference":
                continue
            if category == "value":
                node = _TypeNode("nullable", children=(node,))
            else:
                node = _TypeNode("annotated", children=(node,))
            continue
        break
    return node


def _parse_tuple(stream: _TokenStream) -> _TypeNode:
    stream.expect("(")
    elements: list[_TypeNode] = []
    while True:
        elements.append(_parse_type(stream))
        if _is_identifier(stream.peek()) and _tuple_name_is_terminal(stream):
            stream.take()
        if stream.accept(","):
            continue
        stream.expect(")")
        break
    return _TypeNode("tuple", children=tuple(elements))


def _tuple_name_is_terminal(stream: _TokenStream) -> bool:
    position = stream._position + 1
    if position >= len(stream._tokens):
        return False
    return stream._tokens[position] in {",", ")"}


def _parse_named(stream: _TokenStream) -> _TypeNode:
    stream.accept("global::")
    first = stream.take()
    if not _is_identifier(first):
        raise _ParseError("expected a named type")

    parts = [first]
    while stream.accept("."):
        part = stream.take()
        if not _is_identifier(part):
            raise _ParseError("expected a qualified type segment")
        parts.append(part)
    if stream.peek() == "::":
        raise _ParseError("extern aliases are outside the structured subset")

    arguments: list[_TypeNode] = []
    if stream.accept("<"):
        while True:
            arguments.append(_parse_type(stream))
            if stream.accept(","):
                continue
            stream.expect(">")
            break

    raw_name = ".".join(parts)
    canonical_name = _normalize_named_identity(raw_name)
    node = _TypeNode("named", name=canonical_name, children=tuple(arguments))
    if (
        canonical_name == "System.Nullable"
        and len(arguments) == 1
        and _type_category(arguments[0]) == "value"
    ):
        return _TypeNode("nullable", children=(arguments[0],))
    return node


def _normalize_named_identity(name: str) -> str:
    if name in _ALIASES:
        return _ALIASES[name]
    if "." not in name and name in _WELL_KNOWN_TYPES:
        return _WELL_KNOWN_TYPES[name]
    return name


def _type_category(node: _TypeNode) -> str:
    if node.kind == "array":
        return "reference"
    if node.kind in {"tuple", "nullable"}:
        return "value"
    if node.kind != "named":
        return "unknown"
    if node.name in _KNOWN_REFERENCE_TYPES:
        return "reference"
    if node.name in _KNOWN_VALUE_TYPES:
        return "value"
    return "unknown"


def _render(node: _TypeNode) -> str:
    if node.kind == "named":
        if not node.children:
            return node.name
        return f"{node.name}<{','.join(_render(child) for child in node.children)}>"
    if node.kind == "tuple":
        return f"({','.join(_render(child) for child in node.children)})"
    if node.kind == "array":
        return f"{_render(node.children[0])}[{',' * (node.rank - 1)}]"
    if node.kind == "nullable":
        return f"System.Nullable<{_render(node.children[0])}>"
    if node.kind == "annotated":
        return f"{_render(node.children[0])}?"
    raise AssertionError(f"unknown C# type node: {node.kind}")


def _fallback_normalize(tokens: list[str]) -> str:
    canonical: list[str] = []
    for token in tokens:
        if token == "global::":
            continue
        alias = _ALIASES.get(token)
        if alias is None:
            canonical.append(token)
            continue
        for index, part in enumerate(alias.split(".")):
            if index:
                canonical.append(".")
            canonical.append(part)
    return " ".join(canonical)


def _is_identifier(token: Optional[str]) -> bool:
    if not token:
        return False
    if token[0] == "@":
        token = token[1:]
    return (
        bool(token)
        and (token[0].isalpha() or token[0] == "_")
        and all(character.isalnum() or character == "_" for character in token[1:])
    )
