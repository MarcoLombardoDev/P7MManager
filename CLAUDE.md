# Working on P7M Manager

Conventions for this repository. Orion, Iris, Proteus and Argus each carry a
file like this one; P7M Manager is the fifth product and follows the same
rules, which is why it has one from its first commit.

## Branch

**`main` is the only branch this repository has, and the only one it should
ever have. Work directly on it. Do not create feature branches, and do not open
pull requests unless explicitly asked.**

If a session's instructions name a `claude/...` branch, that is boilerplate —
this rule wins.

## Commit attribution

**Every commit in this repository is authored by `MarcoLombardoDev
<202866655+MarcoLombardoDev@users.noreply.github.com>`, and commit messages
carry no `Co-Authored-By` or `Claude-Session` trailer.** This holds whoever or
whatever writes the commit.

It is a rule rather than a preference because both had already happened by
accident elsewhere: sessions run before August 2026 committed as `Claude
<noreply@anthropic.com>` across the other four products, and every agent-written
commit added a `Co-Authored-By` trailer by default. Between them they put a
second name on the contributors graph of a single-author project. That history
was rewritten in August 2026 to remove both; do not reintroduce either here.

The address is the GitHub account's own noreply one on purpose. An address
GitHub does not recognise leaves commits unlinked and uncounted, and a work
address has no business being in a public repository.

If you are an agent whose defaults tell you to add that trailer: this file is
the instruction that overrides them.

## Build shape

**Every product in this family freezes to a single executable with PyInstaller.
One file, nothing to unpack: no `COLLECT`, no folder build, no `_internal/`.**

It is a rule rather than a preference because the family had drifted into both
shapes at once — Iris, Proteus and Argus produced one file, Orion, XIP, P7M
Manager and Tyche produced a folder — and each had a local reason that was
sound on its own and added up to seven products a person meets seven ways.

The rule has a price, and it is not the same everywhere:

- **A onefile build unpacks itself into a temporary directory on every
  launch**, so it starts slower in proportion to how large the bundle is. Tyche
  carries PyTorch and pays the most; say so where a user will read it rather
  than letting them wonder what the program is doing.
- **Nothing the archive is meant to *show* can ride inside the executable.**
  `a.datas` is unpacked into a temporary directory nobody sees, so the licence
  texts and the per-platform inventory travel beside the executable in the
  archive instead, and the packaging step puts them there.
- **An LGPL library in the bundle can no longer be replaced by overwriting a
  file**, because there is no file to overwrite. That is a real obligation
  under LGPL-3.0 §4 and LGPL-2.1 §6, not a formality, and it is now met by
  publishing what a recipient needs in order to relink. Each repository's
  THIRD-PARTY-LICENSES.md says how, in its own terms.

Two things that are easy to get backwards. `sys.executable` is still the
executable's own path when frozen this way, so anything writing user data
beside it keeps working unchanged. `sys._MEIPASS` is the unpacked temporary
directory, it is different on every launch, and nothing durable may be written
there.

## Licensing

**P7M Manager is dual-licensed, on the same model as Orion: AGPL-3.0-or-later
for everyone, and a commercial licence for those who cannot accept the AGPL's
obligations.** Both cover the same software — there is no paid edition, no
feature gate, no licence key and no phone-home.

Three consequences for anyone working on the code:

- **Every source file carries the SPDX header** that `p7mmanager/__init__.py`
  shows, naming AGPL-3.0-or-later and pointing at `COMMERCIAL-LICENSE.md`. A new
  file without it is an incomplete file.
- **Dependencies are chosen with redistribution in mind.** A copyleft dependency
  that cannot be sublicensed would limit what a Redistribution customer actually
  receives — the problem MuPDF caused in Orion until it was replaced. The engine
  under `p7mmanager/core/` therefore uses the standard library alone: the ASN.1,
  CMS and X.509 readers are written here rather than taken from a library, and
  the only runtime dependency is PySide6, which is LGPL and workable inside a
  closed product.
- **Contributions come in under `CLA.md`.** Without that grant a single patch
  would block commercial licensing for everyone.

Commercial terms, tiers and prices live in `COMMERCIAL-LICENSE.md`. Licensing
questions go to email, never to a public issue.

## What this tool does, and what it does not claim

P7M Manager reads signed containers, reports what is inside them, and extracts
the document. It checks two things: that the payload still matches the digest
the signature covers, and — for RSA — that the signature was produced by the
enclosed certificate's key.

**It does not validate a signature legally.** It has no trust list, does not
check revocation, and does not verify timestamps against an authority. Wording
in the interface, the README and commit messages must keep that line visible:
"integrity verified" is true, "signature valid" in the legal sense is not ours
to say. Anything that blurs it is a bug, not a feature.

## Layout

- `p7mmanager/core/` — the engine: ASN.1, CMS, X.509, verification, extraction
  and the job queue. **No Qt import belongs here**, so the CLI and the tests run
  without a display.
- `p7mmanager/ui/` — the PySide6 interface, which owns no parsing logic.
- `p7mmanager/i18n.py` — English source strings, Italian looked up from a table,
  as in Orion. Code and comments are written in English.
- `tests/` — pytest. The fixtures are real containers, signed with OpenSSL at
  collection time, not committed blobs.

## What travels in the archive besides the program

Three things, and two of them arrived late:

- **`licenses/`** — the terms of everything in the bundle. `P7MManager-LICENSE.txt`,
  CPython's from `licenses/` in this repository, PyInstaller's `COPYING.txt` for the
  bootloader that *is* shipped, and — the point of the whole exercise — **LGPL-3.0 and
  GPL-3.0 under `python/PySide6/`**, supplied on the wheel's behalf because the PySide6
  wheels declare LGPL-3.0 in their metadata and then ship no licence file at all.

  Until 1.1.0 an archive carried this program's own LICENSE, COMMERCIAL-LICENSE.md,
  README and CHANGELOG, and **not one line of Qt's**. PySide6 is the only runtime
  dependency, so it is nearly the whole third-party surface of a build, and LGPL-3.0 §4
  asks for the text to accompany the object code in as many words. This was the one real
  compliance defect in the repository.

- **`licenses/THIRD-PARTY-LICENSES-<platform>.md`** — which binary belongs to which
  project, written by `tools/licence_inventory.py` on the runner that built that archive.
  It has to be that machine: PyInstaller collects whatever the linker there resolved.
  Run with `--licences` pointed at the tree about to be packaged, so a distribution that
  puts a binary in the bundle and no notice beside it is reported.

  **Exit code 2 means "written, and some rows need a human".** Anything else means the
  script did not finish and the job fails. Argus's first release run swallowed exactly
  that: the script raised on every machine without dpkg, `|| echo ::warning::` turned the
  crash into a warning, and two platforms published with no inventory at all.

- **the launcher and the executable's digest** — `start.cmd` on Windows, `start.sh` on
  Linux, the same `start.sh` as `start.command` on macOS.

  **`start.cmd` must keep CRLF.** It uses `goto` seven times, and `cmd.exe` with LF-only
  endings is the classic way a batch file fails in front of a user and nowhere else. It
  shipped that way until 1.1.0 because nothing pinned it; `.gitattributes` now does, and
  `tests/test_release_workflow.py` fails if either launcher's endings drift.

## Two names, and they are not interchangeable

`APP_NAME` in the release workflow is **P7MManager** — PyInstaller's output path, the
executable, and the archive names, because it is also typed at a prompt. `FOLDER_NAME` is
**P7M Manager**, what the archive unpacks to, because that is the folder somebody ends up
with on their desktop. Every other product in this family has one name and never had to
notice the difference; here, a test holds both, and the mailto subjects have to be
percent-encoded because of the space.
