# Contributing

## Getting set up

```sh
uv sync
uv run pytest
uv run ruff check
uv run ruff format
uv run mypy
```

CI runs exactly these, on Python 3.12, 3.13 and 3.14, plus a 90% coverage floor.

## Layout

| Module | Holds |
|---|---|
| `constants.py` | shared literals — the template suffix, `*`, the path separator |
| `models.py` | `YAMLValue`, `Outcome`, `Result`, `Stats` |
| `errors.py` | `ConfigError`, `ParseError` |
| `sections.py` | flat section paths and wildcard matching |
| `document.py` | reading, rendering and atomically rewriting YAML text |
| `detect.py` | mapping a document to a template type |
| `templates.py` | loading templates, flattening them into key orders |
| `sorter.py` | applying a key order to a parsed document |
| `audit.py` | reporting keys no template mentions |
| `processor.py` | one file, end to end |
| `tool.py` | one run, over many paths |
| `cli.py` | argument parsing and logging setup |

`__init__.py` re-exports the public surface and nothing else.

## What a change needs

- A test. Bug fixes get a test that fails before the fix.
- A `CHANGELOG.md` entry under `Unreleased`, if it is user-visible.
- No new public name without a docstring saying *why*, not *what*.

The one rule worth stating outright: **never lose what a manifest carries.** Comments,
anchors, merge keys, quoting, line endings and file permissions all survive a rewrite,
or the rewrite does not happen. When a round-trip cannot preserve something, the file
is skipped with a reason rather than written.

## Releasing

1. Set the version in `pyproject.toml`.
2. Move `Unreleased` in `CHANGELOG.md` to the new version.
3. Tag `vX.Y.Z` and push. The release workflow checks the tag against the packaged
   version, builds, attests and publishes to PyPI via trusted publishing.
