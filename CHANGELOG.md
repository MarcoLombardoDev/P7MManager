# Changelog

All notable changes to P7M Manager are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-09-17

First release.

### Added

- **Signature inspection.** ASN.1/BER, CMS `SignedData` and X.509 readers written against
  the standard library: signers, signing time, digest and signature algorithms, the
  signer's certificate with its subject, issuer, serial, validity window, key, qualified
  statements and SHA-256 fingerprint, plus counter-signatures and RFC 3161 timestamps.
- **Integrity and RSA signature checks.** The enclosed document is hashed and compared with
  the digest the signature covers; RSA PKCS#1 v1.5 signatures are verified against the
  enclosed certificate's key. ECDSA and RSA-PSS are reported as not verified rather than
  guessed at. No trust list, no revocation, no timestamp validation — this is not a legal
  validation, and the interface says so.
- **Extraction.** PDF, XML, OOXML, images, archives and anything else the container holds,
  written atomically beside the original, into one folder, or into a mirror of the source
  tree. Existing files can be renamed around, overwritten or skipped.
- **Containers that are not plain DER**: base64 and PEM-armoured files as some PEC
  providers deliver them, envelopes nested up to eight deep, and detached signatures, which
  are reported rather than silently producing nothing.
- **A recovery fallback.** When the CMS structure cannot be read at all, the file is
  searched for an embedded PDF — what the shell scripts this tool replaces did for every
  file.
- **The queue.** Single files or whole folders, scanned recursively, processed by a pool of
  worker threads, cancellable, re-runnable, with per-file status and a details panel.
- **Reports.** CSV (Excel-safe UTF-8 BOM, semicolon-separated) and JSON, carrying the
  evidence an audit asks for rather than only whether a file was written.
- **A command line** (`--cli`) covering the same engine, including the `-r` and `-d`
  behaviour of the PowerShell and Python scripts this tool replaces.
- **English and Italian**, with a test that fails on any interface phrase missing its
  Italian.
- **Downloadable builds.** A release workflow builds a Windows executable, a macOS bundle
  and a Linux binary on their own runners, smoke-tests each one — `--self-check` brings up
  Qt and reports which platform plugin it loaded, because a bundle missing its plugin
  passes `--version` and then fails on a desktop — and attaches the archives, licence texts
  included, to the release for the tag.
- **The name, the version and the copyright, on screen.** The title bar carries the tool
  and its version, the status bar carries the Appropriate Legal Notice AGPL-3.0 section 5
  asks for — copyright, licence and the address for commercial enquiries — and an About box
  adds the Python and Qt versions a bug report needs, alongside the limits of what the tool
  checks.
