# Schema reference

Macawiki v0.1 stores JSON-compatible YAML between Markdown frontmatter fences. All keys and strings therefore follow JSON syntax while remaining valid YAML.

## Common fields

- `id`: stable lowercase ID using letters, digits, and hyphens.
- `title`, `summary`: human-facing title and one-sentence scope.
- `type`: one of the page types in `data/schemas.yaml`.
- `status`: `draft`, `reviewed`, `deprecated`, or `superseded`.
- `languages`: content languages.
- `tags`, `components`, `hardware`: controlled vocabulary.
- `mxmaca_versions`: explicit software-stack scope; use `unspecified` when unknown.
- `sources`: evidence IDs. Formal wiki pages require at least one source.
- `related`, `prerequisites`: page IDs.
- `verified_at`: last evidence review date, not necessarily independent reproduction.

## Confidence

- `verified`: official evidence plus pinned code or reproducible experiment, approved by a maintainer.
- `source-reported`: stated by an authoritative source but not independently reproduced here.
- `corroborated`: supported by at least two independent public sources.
- `inferred`: derived from evidence; the reasoning chain must be explicit.
- `experimental`: unstable or environment-specific behavior.
- `unknown`: insufficient evidence; allowed only for candidates or source records.

## Reproducibility

`concept < procedure < snippet < runnable < benchmarked`

## Source pages

Source pages add URL, source category, retrieval date, license status, and source-specific version or ref fields. Keep their body faithful to one source.

## Wiki pages

Wiki pages add confidence, reproducibility, prerequisites, and at least one evidence source. Version-sensitive pages should use `version_sensitive` IDs registered in `data/version-claims.yaml`.

## Artifacts

Any future `artifacts/**/PROVENANCE.yaml` must contain `origin_url`, `license`, `retrieved_at`, `asset_mode`, and a file manifest with SHA-256 values. Unknown or restricted licenses must be deferred rather than copied.
