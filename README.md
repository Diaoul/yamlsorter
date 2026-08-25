# yamlsorter

[![ci](https://github.com/Diaoul/yamlsorter/actions/workflows/ci.yaml/badge.svg)](https://github.com/Diaoul/yamlsorter/actions/workflows/ci.yaml)
[![PyPI](https://img.shields.io/pypi/v/yamlsorter)](https://pypi.org/project/yamlsorter/)
[![Python](https://img.shields.io/pypi/pyversions/yamlsorter)](https://pypi.org/project/yamlsorter/)

Reorder keys in Kubernetes and Flux manifests so diffs stay readable. Key order carries
no meaning to Kubernetes, so it is free to standardise — and worth standardising,
because an unordered `spec` makes every review hunt for the field it cares about.

The desired order is declared by example: a template is a manifest whose **keys**
define the order for its type — a skeleton kept in a config directory, or an ordinary
manifest already in the repo. Values are ignored either way.

## Install

```sh
uvx yamlsorter --help          # run without installing
uv tool install yamlsorter     # or install it
pip install yamlsorter
```

## Usage

```sh
yamlsorter kubernetes                    # sort in place
yamlsorter kubernetes --check            # report only, exit 1 if unsorted
yamlsorter kubernetes --audit            # list keys no template covers
yamlsorter kubernetes/apps/media/sonarr/app/helmrelease.yaml
```

Templates are read from `.yamlsorter/` by default; override with `--config-dir`, or
point at any manifest with `--template`:

```sh
yamlsorter kubernetes --template kubernetes/apps/default/vaultwarden/app/helmrelease.yaml
```

Walking a directory picks up `helmrelease.yaml`, `kustomization.yaml` and `ks.yaml`.
`--names` overrides that, repeated or comma-separated —
`--names ks.yaml --names route.yaml`, or `--names ks.yaml,route.yaml`. A file named
explicitly is processed whatever it is called.
A document whose type has no template — a Secret, an OCIRepository — is skipped, not
an error.

A rewrite never loses what a manifest carries: comments, anchors, `<<` merge keys,
quoting, line endings and file permissions all survive. Keys inherited through a merge
stay with their anchor rather than being copied in. Where a round-trip cannot preserve
something — a comment sitting after a list dash, which ruamel re-anchors to the
previous entry, or one above the opening `---`, which it drops — the file is skipped
with a reason instead of being rewritten.

## Templates

One skeleton per document type, in the config directory:

| Template | Applies to |
|---|---|
| `flux-kustomization.yaml.tpl` | `kustomize.toolkit.fluxcd.io` Kustomizations (`ks.yaml`) |
| `kustomization.yaml.tpl` | `kustomize.config.k8s.io` Kustomizations |
| `component.yaml.tpl` | Kustomize Components |
| `helmrelease-apptemplate.yaml.tpl` | HelmReleases whose `chartRef` is `app-template` |
| `helmrelease.yaml.tpl` | every other HelmRelease |

Keys absent from a template keep their relative order and sort after the templated
ones, so a template never has to be exhaustive — `--audit` lists what it is missing.

A HelmRelease resolves to `helmrelease-<chart>.yaml.tpl` (hyphens stripped) by
`chartRef.name`, falling back to `helmrelease.yaml.tpl`. Adding
`helmrelease-cilium.yaml.tpl` is enough to give Cilium its own ordering.

A `"*"` key in a template stands for whatever name the manifest uses at that level, so
one `controllers."*".containers."*"` entry orders every container in the repo.

### Any manifest can be a template

Only a template's keys are read, so an ordinary manifest already in the repo is a
valid template — there is nothing to keep in sync with a parallel skeleton.

```sh
yamlsorter kubernetes --template kubernetes/apps/default/vaultwarden/app/helmrelease.yaml
yamlsorter kubernetes --template httproute=kubernetes/apps/default/echo/app/route.yaml
```

Without a `TYPE=` prefix the template registers for its own `kind`, so the first line
orders every HelmRelease. `--template` is repeatable and beats the config directory.

Any `kind` has a type: `HTTPRoute` is `httproute`, `OCIRepository` is `ocirepository`.
Give one a template — by path, or as `<type>.yaml.tpl` in the config directory — and
its documents get sorted; documents with no template are still skipped, not an error.
Remember `--names route.yaml` when walking a directory, since only
`helmrelease.yaml`, `kustomization.yaml` and `ks.yaml` are picked up by default.

Files in the config directory may be named `<type>.yaml.tpl`, `.yml.tpl`, `.yaml` or
`.yml`; the `.tpl` forms win when both exist.

The `.tpl` suffix is load-bearing **for skeletons**. A skeleton is a well-formed
Kustomization or HelmRelease, so under a plain `.yaml` name repo-wide Flux scanners
render it as a real resource — Konflate reads `dependsOn: [{name: dependency}]` out of
the placeholder and reports a dependency failure per app. A template supplied with
`--template` is exempt: it is a real manifest the repo already applies, so it has
nothing to hide from.

A working set for a Flux repo is in [`examples/templates/`](examples/templates).

## pre-commit

```yaml
repos:
  - repo: https://github.com/Diaoul/yamlsorter
    rev: v0.2.0
    hooks:
      - id: yamlsorter
        args: [--config-dir, .yamlsorter]
```

Run it before any YAML formatter: it rewrites key order, and the formatter has to
normalise the result.

## lefthook

The same ordering rule applies, and `parallel = false` is what holds it.

```toml
[pre-commit]
parallel = false

[pre-commit.commands.sort-manifests]
priority = 1
run = "uvx yamlsorter@0.2.0 --config-dir .yamlsorter {staged_files}"
glob = ["**/helmrelease.yaml", "**/kustomization.yaml", "**/ks.yaml"]
stage_fixed = true
```

## Development

```sh
uv sync
uv run pytest
uv run ruff check
uv run ruff format --check
uv run mypy
```

The module layout and what a change is expected to carry are in
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
