# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-08-25

### Fixed

- Keys inherited through a `<<` merge are no longer materialised into the document.
  A reorder used to copy the merged keys in, silently severing the link to the anchor
  they came from.
- An empty document (a bare `---`) is kept empty instead of being rewritten as `null`.
- CRLF files keep their line endings instead of being rewritten wholesale as LF.
- A symlinked manifest is written through to its target rather than being replaced by
  a regular file.
- `--audit` now looks inside the levels a `*` stands for, so an unlisted container
  field is reported instead of silently ignored along with the name above it.
- Template lists merge their entries' keys at every depth, not only at the top level.

### Added

- `--template [TYPE=]PATH`, repeatable: use any manifest already in the repo as the
  template for its own `kind`, or for an explicitly named type, instead of maintaining
  a parallel skeleton. Registered templates take precedence over the config directory.
- Templates in the config directory may be named `<type>.yaml`, `<type>.yml`,
  `<type>.yaml.tpl` or `<type>.yml.tpl`; the `.tpl` forms win when both exist.
- `py.typed`, so downstream type checkers see the package's annotations.
- A `.pre-commit-hooks.yaml`, so the tool can be used as a pre-commit hook.

### Changed

- Every `kind` now has a type — `HTTPRoute` is `httproute` — so any document can carry
  a template. `FileTypeDetector.detect` returns `None` for a document with no `kind`
  rather than the `generic` sentinel, and the `GENERIC` constant is gone —
  `Result.file_type` is `None` when no template applied. Documents with no template are still
  skipped rather than failing.
- `--audit` names the template file a type resolved to, rather than assuming
  `<type>.yaml.tpl`.
- The package is split into modules (`templates`, `sorter`, `audit`, `processor`,
  `tool`, `cli`, …). Every public name is still importable from `yamlsorter`.
- `SortingTool` takes `markers=` and `all_caps=` instead of `substitution_markers=`,
  which mixed a sentinel string in with real markers.
- `--version` reads the installed distribution metadata instead of a hardcoded string.
- `--dry-run` is now an alias of `--check` rather than a second flag.

## [0.1.0] - 2026-08-24

Initial release.

[Unreleased]: https://github.com/Diaoul/yamlsorter/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Diaoul/yamlsorter/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Diaoul/yamlsorter/releases/tag/v0.1.0
