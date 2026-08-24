# yamlsorter

Reorder keys in Kubernetes and Flux manifests so diffs stay readable. Key order carries
no meaning to Kubernetes, so it is free to standardise — and worth standardising,
because an unordered `spec` makes every review hunt for the field it cares about.

The desired order is declared by example: each template is a manifest skeleton whose
**keys** define the order for its type. Values there are placeholders and are ignored.

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

Templates are read from `.yamlsorter/` by default; override with `--config-dir`.

Walking a directory picks up `helmrelease.yaml`, `kustomization.yaml` and `ks.yaml`
(`--names` overrides). A file named explicitly is processed whatever it is called.
Anything the templates do not cover — Secrets, HTTPRoutes, OCIRepositories — is
skipped, not an error.

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

The `.tpl` suffix is load-bearing. A template is a well-formed Kustomization or
HelmRelease, so under a plain `.yaml` name repo-wide Flux scanners render it as a real
resource — Konflate reads `dependsOn: [{name: dependency}]` out of the placeholder and
reports a dependency failure per app.

A working set for a Flux repo is in [`examples/templates/`](examples/templates).

## lefthook

Run it before `yamlfmt`, sequentially — it rewrites key order and the formatter has to
normalise the result.

```toml
[pre-commit]
parallel = false

[pre-commit.commands.sort-manifests]
priority = 1
run = "uvx yamlsorter@0.1.0 --config-dir .yamlsorter {staged_files}"
glob = ["**/helmrelease.yaml", "**/kustomization.yaml", "**/ks.yaml"]
stage_fixed = true
```

## Development

```sh
uv sync
uv run pytest
uv run ruff check
uv run mypy
```

## License

MIT
