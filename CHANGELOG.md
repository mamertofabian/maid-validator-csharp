# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-08-03

### Added

- C#-aware type comparison for built-in aliases, nullable forms, generics,
  arrays, tuples, and qualified well-known framework types while preserving
  raw source spellings in collected artifacts and snapshots.
- Exact overload definition signatures for methods, constructors, and
  top-level functions, including generic arity, by-reference parameters,
  `params` arrays, explicit-interface implementations, and `__arglist`.

### Changed

- Raised the MAID Runner dependency floor to 2.24, the first published release
  containing both validator type-comparison and exact-signature contracts.
- CI and release resolution now use the locked published Runner dependency
  instead of a development-only adjacent checkout.
- Python 3.10 installs now include the `tomli` compatibility dependency used
  by MAID Runner 2.24's configuration loader.

## [0.1.0] - 2026-08-01

### Added

- Initial C# validator plugin for MAID Runner, backed by tree-sitter-c-sharp.
- Public implementation collection for namespaces, types, delegates, methods,
  constructors, properties, fields, and top-level local functions.
- Behavioral reference collection for common xUnit, NUnit, and MSTest syntax.
- Syntax-local receiver, object-initializer, `typeof`, `nameof`, and namespace
  import identity coverage.
- MAID Runner conformance-kit coverage and focused extraction tests.

### Security

- PyPI publication uses GitHub's OIDC Trusted Publishing flow, avoiding a
  long-lived PyPI API token in repository secrets.

[Unreleased]: https://github.com/mamertofabian/maid-validator-csharp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/mamertofabian/maid-validator-csharp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mamertofabian/maid-validator-csharp/releases/tag/v0.1.0
