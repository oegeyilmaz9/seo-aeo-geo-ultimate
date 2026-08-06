# Security policy

## Scope

This repository contains local skill instructions, validators, schemas, and a runtime installer. It should not contain credentials, live analytics exports, customer data, private URLs, access tokens, or copied protected content.

## Reporting a vulnerability

Until a public reporting channel is configured, do not open a public issue for a suspected security vulnerability. Contact the repository maintainer privately and include a minimal reproduction, affected file/version, and impact. Do not include secrets in the report.

## Installer safety

`scripts/install_runtime.py` stages skill copies, blocks symlink/reparse-point paths, hashes installed files, and retains existing target folders in a timestamped backup. Review a `--dry-run` plan before runtime installation, especially on a shared or managed machine.
