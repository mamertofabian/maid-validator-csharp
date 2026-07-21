"""tree-sitter parse-session helpers for the C# validator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from tree_sitter import Parser, Tree


class CSharpParseSession:
    """A parsed C# source file plus any syntax errors found."""

    __slots__ = ("source_bytes", "tree", "parse_errors")

    def __init__(
        self,
        source_bytes: bytes,
        tree: "Tree",
        parse_errors: list[str],
    ) -> None:
        self.source_bytes = source_bytes
        self.tree = tree
        self.parse_errors = parse_errors


def parse_csharp_source(source: str, parser: "Parser") -> CSharpParseSession:
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    return CSharpParseSession(
        source_bytes=source_bytes,
        tree=tree,
        parse_errors=collect_parse_errors(tree.root_node),
    )


def collect_parse_errors(node: Any) -> list[str]:
    """Walk the tree collecting ERROR / missing-node syntax diagnostics."""
    errors: list[str] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type == "ERROR":
            line = current.start_point[0] + 1
            errors.append(f"Syntax error near line {line}")
            continue
        if getattr(current, "is_missing", False):
            line = current.start_point[0] + 1
            errors.append(f"Missing syntax node near line {line}")
            continue
        stack.extend(reversed(current.children))

    if getattr(node, "has_error", False) and not errors:
        errors.append("Syntax error")

    return errors
