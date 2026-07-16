# TGS Custody Manifest Format — v1.0

**Status:** Stable · **Maintainer:** [The Gray Systems](https://thegray.systems) · **Verifier:** [`tgs_verify.py`](./tgs_verify.py)

A **custody manifest** is a machine-readable record that travels with a training-data delivery and makes one promise checkable by anyone: *the data you received is exactly the data that was documented — asset by asset, byte for byte, with its origin and license on the record.*

A manifest documents, per asset: a **SHA-256 content fingerprint**, a **declared origin** (synthetic, recorded, or collected), the **generator model and its license** for synthetic assets, optional **generation parameters**, and the **license class** the delivery ships under. Verification is fully offline and requires no cooperation from the supplier: recompute each fingerprint, compare, done.

This format verifies **delivery integrity and documented provenance**. It intentionally does not describe how assets are produced — a manifest is the certificate, not the factory.

## 1. Container

A manifest is a single UTF-8 JSON object, conventionally named `PN-<project-id>_manifest.json`, shipped at the root of the delivery.

```json
{
  "manifest_type": "tgs-custody-manifest",
  "manifest_version": "1.0",
  "project": {
    "id": "PN-00000000",
    "supplier": "The Gray Systems",
    "url": "https://thegray.systems"
  },
  "created": "2026-07-16T00:00:00Z",
  "license": { "class": "evaluation-only", "terms_url": "" },
  "assets": [ ]
}
```

| Field | Req | Meaning |
|---|---|---|
| `manifest_type` | ✔ | Literal `"tgs-custody-manifest"`. |
| `manifest_version` | ✔ | `"1.x"`. Minor versions only add optional fields. |
| `project.id` | ✔ | Supplier's project number. |
| `project.supplier` / `project.url` | ✔ | Who stands behind the record. |
| `created` | ✔ | ISO-8601 UTC timestamp of manifest creation. |
| `license.class` | ✔ | One of `evaluation-only`, `non-exclusive`, `exclusive`, `full-transfer`. Delivery-level default; assets may override. |
| `license.terms_url` | – | Where the governing terms live. |

## 2. Assets

Each entry in `assets`:

```json
{
  "path": "deliverables/scene_0001.png",
  "sha256": "9f2c…64 lowercase hex…",
  "bytes": 48213,
  "origin": "synthetic",
  "generator": {
    "model": "example-diffusion-xl",
    "version": "1.0",
    "license": "OpenRAIL++"
  },
  "params": { "seed": 12345, "steps": 30 },
  "license": "evaluation-only"
}
```

| Field | Req | Rule |
|---|---|---|
| `path` | ✔ | Relative, forward slashes, no `..`, no absolute paths. |
| `sha256` | ✔ | 64 lowercase hex chars — SHA-256 of the exact delivered bytes. |
| `bytes` | – | File size; verified when present. |
| `origin` | ✔ | `synthetic` (generated), `recorded` (performed/captured to spec, documented consent), `collected` (sourced under documented rights). |
| `generator.model`, `generator.license` | ✔ if synthetic | The generating model and the license it was operated under. `generator.version` recommended. |
| `params` | – | Generation parameters the supplier chooses to disclose. Free-form object. |
| `license` | – | Per-asset override of `license.class`. |

Unknown fields MUST be ignored by verifiers (forward compatibility).

## 3. Verification procedure

A conforming verifier:

1. Parses the manifest; rejects it (`ERROR`) if unreadable.
2. Validates the structural rules above; reports violations (`FAILED`).
3. For every asset: locates the file under the delivery root, recomputes SHA-256, compares to the recorded fingerprint, and checks `bytes` when present.
4. Verdicts: **VERIFIED** — all assets present and matching. **FAILED** — any asset missing, altered, mis-sized, or any structural violation. Exit codes `0 / 1 / 2` (verified / failed / manifest error).

A missing file and an altered file are distinct findings and MUST be reported as such.

## 4. CSV delivery manifests

Deliveries may also carry a flat CSV manifest (one row per file with at minimum a filename column and a SHA-256 column). CSV manifests support fingerprint verification only — provenance fields live in the JSON form. The reference verifier accepts them via `--csv` with header auto-detection.

## 5. Roadmap (v1.1, planned)

- `signature` block: Ed25519 signature over the canonicalized manifest, so the *manifest itself* is tamper-evident and attributable to the supplier's published key.
- `manifest_sha256` self-fingerprint convention for detached distribution.

## 6. What this spec is not

Not a watermarking scheme, not a generation-quality standard, not a legal opinion. It is the minimal, checkable layer underneath all three: proof that what was documented is what was delivered.
