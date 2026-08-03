# Releasing

Releases use GitHub Actions and a PyPI Trusted Publisher. Do not add a PyPI API
token to repository secrets.

## One-time setup

Before the first release, add a pending publisher in the PyPI account's
Publishing settings with these exact values:

- PyPI project name: `maid-validator-csharp`
- GitHub owner: `mamertofabian`
- GitHub repository: `maid-validator-csharp`
- Workflow filename: `publish.yml`
- Environment name: `pypi`

Create the `pypi` GitHub environment as well. Environment protection rules may
require approval before the publish job receives its short-lived OIDC token.

## Release checklist

1. Start from a clean, up-to-date `main` branch.
2. Update `project.version` in `pyproject.toml` and move the release notes from
   `Unreleased` into a dated changelog entry.
3. Confirm MAID Runner 2.24.0 or newer is published. Version 2.24.0 is the first
   release containing both `BaseValidator.types_match` and exact callable
   signatures. Keep the `maid-runner` lower bound at `>=2.24` or newer.
4. Confirm no development-only `[tool.uv.sources]` table is present. If one was
   introduced for later development, remove it and refresh the lock from
   package indexes:

   ```bash
   uv lock --refresh
   uv lock --check
   ```

   Verify that neither `pyproject.toml` nor `uv.lock` contains the adjacent
   `../maid-runner` editable source before continuing.
5. Run the repository gates with the published Runner resolution:

   ```bash
   uv run pytest -q
   uv run ruff check src/ tests/
   uv run black --check src/ tests/
   uv run maid validate
   uv run maid test
   ```

6. Build and inspect the exact release artifacts locally:

   ```bash
   uv build
   uvx --from twine==7.0.0 twine check dist/*
   ```

7. Install the built wheel in an isolated environment and confirm
   `CSharpValidator` is discovered and constructs successfully with the
   published Runner dependency. This is required in addition to testing the
   editable source checkout.
8. After the reviewed release commit is on `main`, create and push the matching
   annotated tag. For release 0.2.0:

   ```bash
   git tag -a v0.2.0 -m "Release maid-validator-csharp 0.2.0"
   git push origin v0.2.0
   ```

The publish workflow rejects tags whose commit is not on `main` or whose version
does not exactly match `project.version`. A successful tag run tests every
supported Python version, builds and checks the wheel and source distribution,
installs the wheel in an isolated environment to verify validator discovery,
publishes the artifacts to PyPI, and attaches them to a generated GitHub Release.

## Post-release verification

Install from PyPI in a new environment and confirm discovery:

```bash
uvx --from maid-validator-csharp maid validators
```

The output must show `CSharpValidator`, extension `.cs`, source
`maid-validator-csharp <version>`, and status `active`.
