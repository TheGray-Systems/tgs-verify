# tgs-verify

**tgs-verify is the open verifier for [The Gray Systems](https://thegray.systems) custody manifests — the per-asset provenance record (origin, generator model and license, generation parameters, SHA-256 content fingerprint) that ships with every TGS training-data delivery.** Point it at a manifest and the delivered files; it recomputes every fingerprint and tells you, loudly, whether the data you received is exactly the data that was documented.

Single file. Zero dependencies. Python 3.8+. Fully offline — verification never phones home and requires nothing from the supplier.

## 30-second demo

```bash
git clone https://github.com/thegray-systems/tgs-verify && cd tgs-verify
python3 tgs_verify.py examples/manifest.json
```

```
tgs-verify 1.0.0 — 3 asset(s), root: examples
  ✓ assets/scene_0001.png  c0c4002a61f8…
  ✓ assets/scene_0002.png  87226cc1ea67…
  ✓ assets/scene_0003.png  be0eb7f19036…
✓ VERIFIED — 3/3 assets match their custody record
```

Now watch it catch tampering — one pixel changed in one asset:

```bash
python3 tgs_verify.py examples/manifest.json --root examples/tampered
```

```
  ✓ assets/scene_0001.png  …
  ✗ ALTERED   assets/scene_0002.png
      expected 87226cc1…
      actual   a41647e1…
  ✓ assets/scene_0003.png  …
✗ FAILED — 2/3 assets match their custody record
```

## Usage

```bash
python3 tgs_verify.py <manifest.json> [--root DIR]     # verify a JSON custody manifest
python3 tgs_verify.py --csv PN-123_manifest.csv --root ./delivery   # verify a delivery CSV
python3 tgs_verify.py manifest.json --json             # machine-readable report
```

Exit codes: `0` verified · `1` failed · `2` manifest unreadable. Wire it into CI and a bad delivery fails your pipeline before it touches training.

## What a custody manifest records

Every asset in a TGS delivery carries: a **SHA-256 fingerprint** of the exact delivered bytes, a **declared origin** (`synthetic` / `recorded` / `collected`), for synthetic assets the **generator model, version, and the license it was operated under**, optional **generation parameters**, and the **license class** the data ships under (`evaluation-only`, `non-exclusive`, `training-only`, `exclusive`, `full-ip-buyout`, `custom`). The full format is defined in [SPEC.md](./SPEC.md).

The verifier checks the certificate, not the factory: it proves delivery integrity and documented provenance without exposing anything about how data is produced.

## Why this exists

Training-data provenance fails quietly. A dataset changes hands, a file gets re-encoded, a folder gets "helpfully" cleaned up — and the record no longer matches reality, which surfaces months later in diligence, an audit, or a lawsuit. A custody manifest plus an open verifier makes the failure loud and immediate instead: anyone in the chain — buyer, counsel, auditor, acquirer — can re-check the delivery in seconds, forever, without trusting the supplier's word.

## Roadmap

- **v1.1** — Ed25519 manifest signatures (tamper-evident, attributable manifests) per SPEC §5.

## License

MIT. The manifest format (SPEC.md) is open for anyone to implement — verifiers, generators, or both.
