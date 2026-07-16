#!/usr/bin/env python3
"""tgs-verify — open verifier for TGS custody manifests.

Verifies that a delivered dataset matches its custody manifest:
every asset present, every SHA-256 fingerprint identical, every
required provenance field populated.

The Gray Systems — https://thegray.systems
Spec: SPEC.md (TGS Custody Manifest Format v1)

Zero dependencies. Python 3.8+.

Usage:
    python3 tgs_verify.py <manifest.json> [--root DIR] [--json] [--quiet]
    python3 tgs_verify.py --csv <manifest.csv> --root DIR [--json] [--quiet]

Exit codes:
    0  VERIFIED  — every check passed
    1  FAILED    — one or more assets missing, altered, or undocumented fields invalid
    2  ERROR     — manifest unreadable or malformed
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys

SPEC_VERSION = "1.0"
TOOL_VERSION = "1.0.0"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ORIGINS = {"synthetic", "recorded", "collected"}
LICENSE_CLASSES = {"evaluation-only", "non-exclusive", "exclusive", "full-transfer"}

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def _color(enabled):
    if enabled and sys.stdout.isatty():
        return GREEN, RED, YELLOW, DIM, RESET
    return "", "", "", "", ""


def sha256_file(path, bufsize=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(bufsize)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- JSON mode

def load_json_manifest(path):
    """Parse and structurally validate a v1 JSON manifest.

    Returns (manifest_dict, structural_errors)."""
    with open(path, "r", encoding="utf-8") as f:
        m = json.load(f)

    errs = []
    if m.get("manifest_type") != "tgs-custody-manifest":
        errs.append('manifest_type must be "tgs-custody-manifest"')
    if not str(m.get("manifest_version", "")).startswith("1."):
        errs.append('manifest_version must be a "1.x" version')
    if not isinstance(m.get("assets"), list) or not m["assets"]:
        errs.append('"assets" must be a non-empty list')
        return m, errs

    lic = m.get("license", {})
    if lic and lic.get("class") not in LICENSE_CLASSES:
        errs.append('license.class must be one of: %s' % ", ".join(sorted(LICENSE_CLASSES)))

    for i, a in enumerate(m["assets"]):
        tag = a.get("path", "asset #%d" % i)
        if not a.get("path"):
            errs.append("asset #%d: missing path" % i)
        if os.path.isabs(a.get("path", "")) or ".." in a.get("path", "").split("/"):
            errs.append("%s: path must be relative, no '..'" % tag)
        if not SHA256_RE.match(str(a.get("sha256", ""))):
            errs.append("%s: sha256 missing or not 64 lowercase hex chars" % tag)
        if a.get("origin") not in ORIGINS:
            errs.append("%s: origin must be one of: %s" % (tag, ", ".join(sorted(ORIGINS))))
        if a.get("origin") == "synthetic":
            gen = a.get("generator") or {}
            for field in ("model", "license"):
                if not gen.get(field):
                    errs.append("%s: synthetic asset requires generator.%s" % (tag, field))
        if "bytes" in a and not isinstance(a["bytes"], int):
            errs.append("%s: bytes must be an integer" % tag)

    return m, errs


def iter_json_assets(m):
    for a in m["assets"]:
        yield a["path"], a.get("sha256", ""), a.get("bytes")


# ----------------------------------------------------------------- CSV mode

def load_csv_manifest(path):
    """Column auto-detection for delivery manifest CSVs.

    Finds the filename/path column and the SHA-256 column by header name;
    falls back to value sniffing (a column whose values look like SHA-256)."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise ValueError("CSV has no data rows")

    header = [c.strip().lower() for c in rows[0]]

    def find(*keys):
        for i, h in enumerate(header):
            if any(k in h for k in keys):
                return i
        return None

    sha_col = find("sha-256", "sha256", "fingerprint", "hash", "digest")
    path_col = find("path", "file", "name", "asset")
    size_col = find("bytes", "size")

    if sha_col is None:  # sniff: column where every data value is 64 hex chars
        for i in range(len(header)):
            vals = [r[i].strip().lower() for r in rows[1:] if i < len(r)]
            if vals and all(SHA256_RE.match(v) for v in vals):
                sha_col = i
                break
    if sha_col is None:
        raise ValueError("could not locate a SHA-256 column (header or values)")
    if path_col is None or path_col == sha_col:
        raise ValueError("could not locate a filename/path column")

    assets = []
    for r in rows[1:]:
        if len(r) <= max(sha_col, path_col):
            continue
        size = None
        if size_col is not None and size_col < len(r):
            digits = re.sub(r"[^0-9]", "", r[size_col])
            size = int(digits) if digits else None
        assets.append((r[path_col].strip(), r[sha_col].strip().lower(), size))

    if not assets:
        raise ValueError("no asset rows parsed from CSV")
    return assets


# --------------------------------------------------------------------- core

def find_file(root, rel):
    """Exact relative path first; else unique basename match anywhere
    under root (delivery ZIPs sometimes re-root folder structures)."""
    exact = os.path.join(root, rel)
    if os.path.isfile(exact):
        return exact
    base = os.path.basename(rel)
    hits = []
    for dirpath, _dirs, files in os.walk(root):
        if base in files:
            hits.append(os.path.join(dirpath, base))
    return hits[0] if len(hits) == 1 else None


def verify(entries, root, quiet=False, color=True):
    G, R, Y, D, X = _color(color)
    results, failed = [], 0

    for rel, expected, size in entries:
        f = find_file(root, rel)
        if f is None:
            results.append({"path": rel, "status": "MISSING"})
            failed += 1
            if not quiet:
                print("  %s✗ MISSING%s   %s" % (R, X, rel))
            continue

        actual = sha256_file(f)
        if actual != expected:
            results.append({"path": rel, "status": "ALTERED",
                            "expected": expected, "actual": actual})
            failed += 1
            if not quiet:
                print("  %s✗ ALTERED%s   %s" % (R, X, rel))
                print("      expected %s%s%s" % (D, expected, X))
                print("      actual   %s%s%s" % (D, actual, X))
            continue

        if size is not None and os.path.getsize(f) != size:
            results.append({"path": rel, "status": "SIZE_MISMATCH"})
            failed += 1
            if not quiet:
                print("  %s✗ SIZE%s      %s (bytes differ from manifest)" % (R, X, rel))
            continue

        results.append({"path": rel, "status": "OK"})
        if not quiet:
            print("  %s✓%s %s  %s%s…%s" % (G, X, rel, D, expected[:12], X))

    return results, failed


def main(argv=None):
    p = argparse.ArgumentParser(prog="tgs-verify",
                                description="Verify a dataset against its TGS custody manifest.")
    p.add_argument("manifest", help="manifest file (JSON per SPEC.md, or CSV with --csv)")
    p.add_argument("--csv", action="store_true", help="treat manifest as a delivery CSV")
    p.add_argument("--root", default=None, help="directory holding the assets "
                   "(default: the manifest's own directory)")
    p.add_argument("--json", action="store_true", help="machine-readable JSON report on stdout")
    p.add_argument("--quiet", action="store_true", help="verdict line only")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--version", action="version", version="tgs-verify %s (spec %s)"
                   % (TOOL_VERSION, SPEC_VERSION))
    args = p.parse_args(argv)

    root = args.root or os.path.dirname(os.path.abspath(args.manifest))
    quiet = args.quiet or args.json
    G, R, Y, D, X = _color(not args.no_color)

    try:
        if args.csv:
            entries = load_csv_manifest(args.manifest)
            struct_errs = []
        else:
            m, struct_errs = load_json_manifest(args.manifest)
            entries = list(iter_json_assets(m)) if "assets" in m and isinstance(m["assets"], list) else []
    except Exception as e:
        msg = "manifest error: %s" % e
        print(json.dumps({"verdict": "ERROR", "error": str(e)}) if args.json
              else "%s%s%s" % (R, msg, X), file=sys.stdout if args.json else sys.stderr)
        return 2

    if struct_errs:
        if args.json:
            print(json.dumps({"verdict": "FAILED", "structural_errors": struct_errs}, indent=2))
        else:
            print("%sStructural errors in manifest:%s" % (R, X))
            for e in struct_errs:
                print("  %s✗%s %s" % (R, X, e))
        return 1

    if not quiet:
        print("tgs-verify %s — %d asset(s), root: %s" % (TOOL_VERSION, len(entries), root))

    results, failed = verify(entries, root, quiet=quiet, color=not args.no_color)
    verdict = "VERIFIED" if failed == 0 else "FAILED"

    if args.json:
        print(json.dumps({"verdict": verdict, "assets": len(results),
                          "failed": failed, "results": results}, indent=2))
    else:
        mark = ("%s✓ VERIFIED%s" % (G, X)) if failed == 0 else ("%s✗ FAILED%s" % (R, X))
        print("%s — %d/%d assets match their custody record"
              % (mark, len(results) - failed, len(results)))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
