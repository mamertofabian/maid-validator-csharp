# maid-validator-csharp

[![CI](https://github.com/mamertofabian/maid-validator-csharp/actions/workflows/ci.yml/badge.svg)](https://github.com/mamertofabian/maid-validator-csharp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/maid-validator-csharp.svg)](https://pypi.org/project/maid-validator-csharp/)
[![Python](https://img.shields.io/pypi/pyversions/maid-validator-csharp.svg)](https://pypi.org/project/maid-validator-csharp/)

A C# (`.cs`) language validator plugin for
[MAID Runner](https://github.com/mamertofabian/maid-runner), backed by
[tree-sitter-c-sharp](https://github.com/tree-sitter/tree-sitter-c-sharp).

It registers through MAID Runner's `maid_runner.validators` entry point, so once
installed alongside `maid-runner`, `maid validate` / `maid snapshot` /
`maid bootstrap` handle `.cs` files with no core changes. This follows MAID
Runner's [validator plugin authoring](https://github.com/mamertofabian/maid-runner/blob/main/docs/validator-plugin-authoring.md)
support boundary: new languages ship as external packages.

## Install

```bash
pip install maid-validator-csharp
# or, for local development against a checked-out maid-runner:
uv pip install -e ../maid-runner -e .
```

Confirm it is active:

```bash
maid validators
# CSharpValidator   .cs   maid-validator-csharp <ver>   active
```

## What it collects

C# constructs are mapped onto MAID's language-neutral artifact kinds:

| C# construct | MAID `kind` | Notes |
|---|---|---|
| `namespace` (block and file-scoped) | `namespace` | |
| `class`, `struct`, `record`, `record struct` | `class` | `bases` = base type + implemented interfaces |
| `interface` | `interface` | members are implicitly public |
| `enum` | `enum` | |
| `delegate` | `type` | records `args` + return type |
| method / constructor | `method` | `of` = declaring type; captures `args` (name/type/default), `returns`, generic `type_parameters`, `async` |
| property / field | `attribute` | `of` = declaring type; captures the declared type |
| top-level local function | `function` | |

Only the **public API surface** is emitted — `public`/`protected` members and
`public` types, interface members, and top-level local functions.
`private`/`internal`/implicitly-private members are dropped, and
leading-underscore names are treated as private (excluded from snapshots).

Behavioral collection (from test files) emits `test_function` markers for
xUnit/NUnit/MSTest methods (`[Fact]`, `[Theory]`, `[Test]`, `[TestMethod]`, …)
and identity references for the types (`new Widget()`) and methods
(`Calc.Add(...)`, `Render(...)`) those tests exercise.

## Development

```bash
uv sync            # installs the locked published dependency graph
uv run pytest -v   # runs the MAID conformance kit + hand-written suites
uv run ruff check src/ tests/
uv run black --check src/ tests/
```

Version 0.2.0 requires MAID Runner 2.24 or newer. That release provides the
language-aware type-comparison and exact callable-signature contracts used by
the plugin. Package and CI resolution use published dependencies; local
editable Runner checkouts are optional development tooling only.

## C# type comparison

Manifest comparison accepts equivalent C# source spellings without changing
the raw types emitted by collection or snapshots. Supported equivalences are:

- every built-in C# keyword/CLR type pair, including native integers and
  `dynamic`/`System.Object`;
- `global::` qualification and explicit `List`, `Dictionary`, `Task`, and
  `Nullable` BCL qualifications;
- nested generics, nullable known value types, nullable annotations on known
  reference types, arrays and their ranks, and tuple element names.

Comparison remains conservative without compiler evidence. Arbitrary custom
names do not collapse across namespaces, unknown `T?` or `Widget?` forms stay
distinct from their unannotated form, and array suffix order, tuple position,
and tuple arity remain significant. Pointer and function-pointer spellings use
a deterministic lexical comparison when they fall outside the structured
subset.

The [MAID conformance kit](https://github.com/mamertofabian/maid-runner/blob/main/docs/validator-plugin-authoring.md#conformance-kit)
(`tests/test_conformance.py`) is the acceptance bar: it proves the collector
cannot manufacture false-green validation for C#.

## Exact overload definitions

Methods, constructors, and top-level functions expose canonical definition
signatures so manifests can select an exact overload. Identity includes method
generic arity, canonical parameter types, C# by-reference semantics,
explicit-interface qualification, and `__arglist`. Raw argument and return
spellings remain source-shaped. Syntax-only behavioral calls intentionally stay
unsigned because tree-sitter cannot bind a call to a compiler-selected overload;
that semantic path remains reserved for optional Roslyn integration.

See [CHANGELOG.md](CHANGELOG.md) for release history and
[RELEASING.md](RELEASING.md) for the trusted-publishing procedure.

## Known limitations

- **Semantic type identity:** syntax-level comparison cannot determine whether
  an arbitrary custom type is a value type, resolve aliases/usings, or prove
  compiler-bound identity. Those cases remain exact until the optional Roslyn
  semantic path is implemented.
- **Module identity:** C# module identity is the in-file `namespace`, not a
  path-derived module, so cross-file `using`/namespace resolution is not yet
  performed; behavioral matching binds on kind/name/parent.
- **Partial classes** are collected per file; cross-file merging is MAID
  Runner's responsibility via manifest chains.
- Parser fidelity is bounded by the tree-sitter-c-sharp grammar. Unparseable or
  unsupported syntax yields a `CollectionResult` with `errors` and no artifacts
  (never a crash).
