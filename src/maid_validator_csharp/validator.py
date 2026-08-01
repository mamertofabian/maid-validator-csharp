"""CSharpValidator: MAID Runner validator plugin for C# (.cs) files.

Backed by tree-sitter-c-sharp. Registered with MAID Runner through the
``maid_runner.validators`` entry point so ``maid validate`` handles ``.cs``
files once this package is installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from maid_runner.validators.base import BaseValidator, CollectionResult

from maid_validator_csharp._behavioral import collect_behavioral_artifacts
from maid_validator_csharp._implementation import collect_implementation_artifacts
from maid_validator_csharp._parse import parse_csharp_source
from maid_validator_csharp._types import csharp_types_match

try:
    from tree_sitter import Language, Parser
    import tree_sitter_c_sharp

    _HAS_TREE_SITTER = True
except ImportError:  # pragma: no cover - exercised only without the grammar
    _HAS_TREE_SITTER = False

_LANGUAGE = "csharp"


class CSharpValidator(BaseValidator):
    def __init__(self) -> None:
        if not callable(getattr(BaseValidator, "types_match", None)):
            raise ImportError(
                "maid-validator-csharp requires a maid-runner release that "
                "provides BaseValidator.types_match"
            )
        if not _HAS_TREE_SITTER:
            raise ImportError(
                "tree-sitter and tree-sitter-c-sharp are required for C# "
                "validation. Install with: pip install maid-validator-csharp"
            )
        self._parser = Parser(Language(tree_sitter_c_sharp.language()))

    @classmethod
    def supported_extensions(cls) -> tuple[str, ...]:
        return (".cs",)

    def types_match(
        self,
        manifest_type: Optional[str],
        implementation_type: Optional[str],
    ) -> bool:
        return csharp_types_match(manifest_type, implementation_type)

    def collect_implementation_artifacts(
        self,
        source: str,
        file_path: Union[str, Path],
    ) -> CollectionResult:
        return self._collect_with_parse_guard(
            language=_LANGUAGE,
            file_path=file_path,
            parse_fn=lambda: parse_csharp_source(source, self._parser),
            collect_fn=lambda session: collect_implementation_artifacts(
                session.tree.root_node, session.source_bytes
            ),
            errors_from_session=lambda session: session.parse_errors,
        )

    def collect_behavioral_artifacts(
        self,
        source: str,
        file_path: Union[str, Path],
    ) -> CollectionResult:
        return self._collect_with_parse_guard(
            language=_LANGUAGE,
            file_path=file_path,
            parse_fn=lambda: parse_csharp_source(source, self._parser),
            collect_fn=lambda session: collect_behavioral_artifacts(
                session.tree.root_node, session.source_bytes
            ),
            errors_from_session=lambda session: session.parse_errors,
        )
