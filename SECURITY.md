# Security Policy

## Reporting a vulnerability

If you find a security issue in tgs-verify — especially anything that could make the
verifier report **VERIFIED** for data that should fail, or **FAILED** for data that
should pass — please report it privately rather than opening a public issue.

- Preferred: GitHub's private vulnerability reporting (Security tab → "Report a vulnerability")
- Or email: contact@thegray.systems with "SECURITY" in the subject

You'll get an acknowledgment within 3 business days. Confirmed issues are fixed in a
patch release and credited in the advisory unless you prefer otherwise.

## Severity model

A false **VERIFIED** — the verifier vouching for data that doesn't match its custody
record — is treated as the highest severity this project can have. Everything else
(crashes, false FAILED, parsing errors on malformed input) matters, but that one is
the reason the tool exists.

## Scope

tgs-verify is a single-file, stdlib-only tool that runs fully offline and makes no
network calls. The security-relevant surface is deliberately small: manifest parsing,
path handling, and SHA-256 comparison.

## Supported versions

The latest release on PyPI (`pip install tgs-verify`).
