#!/usr/bin/env bash
# tgs-verify test suite — runs every check that must pass before a push.
# Exits non-zero on the first failure.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VERIFY="python3 tgs_verify.py"
PASS=0
FAIL=0

check() {
  local desc="$1" expected_exit="$2" actual_exit="$3"
  if [ "$actual_exit" -eq "$expected_exit" ]; then
    echo "PASS: $desc (exit $actual_exit)"
    PASS=$((PASS+1))
  else
    echo "FAIL: $desc (expected exit $expected_exit, got $actual_exit)"
    FAIL=$((FAIL+1))
  fi
}

grep_check() {
  local desc="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -qF -- "$needle"; then
    echo "PASS: $desc"
    PASS=$((PASS+1))
  else
    echo "FAIL: $desc (did not find: $needle)"
    FAIL=$((FAIL+1))
  fi
}

# 1. clean verify
out=$($VERIFY examples/manifest.json --no-color); code=$?
check "clean verify VERIFIED" 0 "$code"
grep_check "clean verify says VERIFIED" "VERIFIED" "$out"

# 2. tampered verify
out=$($VERIFY examples/manifest.json --root examples/tampered --no-color); code=$?
check "tampered verify FAILED" 1 "$code"
grep_check "tampered verify reports ALTERED" "ALTERED" "$out"

# 3. CSV mode
csv=$(mktemp)
python3 -c "
import json, csv
m = json.load(open('examples/manifest.json'))
with open('$csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['File Name','SHA-256 Fingerprint','License','Size','Uploaded'])
    for a in m['assets']:
        w.writerow([a['path'], a['sha256'], a.get('license','evaluation-only'), a['bytes'], '2026-07-16'])
"
out=$($VERIFY --csv "$csv" --root examples --no-color); code=$?
check "CSV mode VERIFIED" 0 "$code"
rm -f "$csv"

# 4. tampered + --json
out=$($VERIFY examples/manifest.json --root examples/tampered --json); code=$?
check "tampered --json FAILED" 1 "$code"
grep_check "tampered --json verdict FAILED" '"verdict": "FAILED"' "$out"
grep_check "tampered --json failed count 1" '"failed": 1' "$out"

# 5. malformed manifest
bad=$(mktemp)
echo '{broken' > "$bad"
$VERIFY "$bad" >/dev/null 2>&1; code=$?
check "malformed manifest ERROR" 2 "$code"
rm -f "$bad"

# 6. valid authored asset
out=$($VERIFY tests/fixtures/authored_valid/manifest.json --no-color); code=$?
check "authored asset VERIFIED" 0 "$code"

# 7. valid derived asset with derived_from
out=$($VERIFY tests/fixtures/derived_valid/manifest.json --no-color); code=$?
check "derived asset with derived_from VERIFIED" 0 "$code"

# 8. derived asset MISSING derived_from — must fail structurally
out=$($VERIFY tests/fixtures/derived_missing_derived_from/manifest.json --no-color 2>&1); code=$?
check "derived asset missing derived_from FAILED" 1 "$code"
grep_check "missing derived_from reported" "derived_from" "$out"

# 9. existing v1.0 manifest using 'supplier' — must still verify
out=$($VERIFY tests/fixtures/v1_0_supplier_alias/manifest.json --no-color); code=$?
check "v1.0 manifest with 'supplier' alias VERIFIED" 0 "$code"

echo ""
echo "== $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
