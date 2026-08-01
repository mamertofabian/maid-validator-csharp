# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/mamertofabian/maid-validator-csharp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mamertofabian/maid-validator-csharp/releases/tag/v0.1.0
