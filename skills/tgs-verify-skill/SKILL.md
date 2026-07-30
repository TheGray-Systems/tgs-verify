---
name: tgs-verify
description: Verify the integrity and provenance of a TGS dataset delivery against its custody manifest (_TGS_MANIFEST.json) before the data is used for anything.
---

## What this verifies

TGS dataset deliveries ship with a **custody manifest** — a JSON file (per-asset SHA-256 fingerprint, declared origin, license class, and for synthetic/derived assets the generating model and its sources) that documents exactly what was delivered. The manifest format is **TGS Custody Manifest Format v1.1**, defined in [`SPEC.md`](../../SPEC.md) at the repo root.

`tgs-verify` recomputes every asset's SHA-256 fingerprint from the actual files on disk and compares it against what the manifest claims, then checks the manifest's own required fields are present and well-formed. It proves the delivery matches its paperwork. It does not evaluate the paperwork's truthfulness beyond what's structurally checkable, and it does not evaluate the assets themselves.

## When to use

Run this against **any TGS delivery folder that contains a custody manifest**, before the assets in it are used for anything — ingested into a pipeline, added to a training set, or handed to a client. Re-run it any time a delivery is re-downloaded, re-copied, or re-extracted, since any of those steps can silently corrupt or re-encode a file.

## How to run

Requires **Python 3.8+**. No other runtime is involved — the verifier has zero dependencies.

```bash
pip install tgs-verify
tgs-verify /path/to/delivery/manifest.json
```

If the assets live in a different directory than the manifest (e.g. the manifest was extracted separately from the delivery), point `--root` at the delivery folder:

```bash
tgs-verify /path/to/manifest.json --root /path/to/delivery
```

For machine-readable output (CI, scripted checks):

```bash
tgs-verify /path/to/manifest.json --json
```

If a delivery ships a flat CSV manifest instead of the JSON form:

```bash
tgs-verify --csv /path/to/manifest.csv --root /path/to/delivery
```

No install needed to just try it against the repo's own bundled example:

```bash
git clone https://github.com/TheGray-Systems/tgs-verify && cd tgs-verify
python3 tgs_verify.py examples/manifest.json
```

## How to read results

Exit code is the ground truth — check it, don't just eyeball the printed output:

- **`0` — VERIFIED.** Every asset was found, every fingerprint matched, every required manifest field was present. The delivery is exactly what was documented. Safe to proceed.
- **`1` — FAILED.** Something in the delivery doesn't match its manifest, or the manifest itself is structurally invalid. Per-asset statuses:
  - `MISSING` — a file the manifest lists isn't present in the delivery.
  - `ALTERED` — the file exists but its recomputed SHA-256 doesn't match the manifest's recorded hash. **This means the bytes you have are not the bytes that were documented** — re-encoding, a partial transfer, corruption, or tampering can all produce this; the verifier can't tell you which.
  - `SIZE_MISMATCH` — file size disagrees with the manifest's recorded `bytes`.
  - A structural error (e.g. a required field missing) is reported as text, not a per-asset row.
- **`2` — ERROR.** The manifest file itself couldn't be read or parsed. No verification was performed at all — this is not the same as FAILED.

**On anything other than exit `0`: stop. Do not use the data.** Contact the vendor/supplier for a corrected delivery or manifest. Do not hand-edit the manifest or the assets to force a match — that defeats the entire point of the check.

## Limits

- This verifies **delivery integrity and documented provenance metadata** — that the files match their fingerprints and that the manifest is well-formed. It says nothing about the **quality, accuracy, or suitability** of the actual content (image quality, whether a synthetic scene looks right, whether a `recorded` asset's consent documentation is genuine).
- A `VERIFIED` verdict is not a license grant. If the manifest's `license.class` is `evaluation-only`, the data is cleared for evaluation only — passing verification does not authorize training or production use. Check `license.class` (and any per-asset `license` override) before using the data for anything beyond what that class permits.
- Ed25519 manifest signatures (making the *manifest itself* tamper-evident, not just the assets it lists) are planned for v1.2 and not yet implemented — a manifest today is only as trustworthy as its transport.
