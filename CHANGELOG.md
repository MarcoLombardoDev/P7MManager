# Changelog

All notable changes to P7M Manager are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] — 2026-09-23

### Changed

- **The archive holds the program, its launcher, its checksum and
  `licenses/`, and nothing else.** It also carried LICENSE,
  COMMERCIAL-LICENSE.md, README.md and CHANGELOG.md in the root — four
  documents in front of somebody who opened it to find a program, one of them
  a second copy of the AGPL that `licenses/P7MManager-LICENSE.txt` already
  carries, and none of them in the other six products' archives. The terms did
  not go anywhere; they are one folder in, where everybody else's are.

### Fixed

- **The console says what the wait actually is.** It said the first launch was
  the slow one because Windows checks every file before running any of them,
  which was true of a folder build. This is one file that unpacks itself into
  a temporary folder before it runs, so the wait is there on *every* start —
  the first one longer still, for the reason the old message gave. Somebody
  watching a console that promises the delay is a one-off, twice, has been
  told something false about their own computer.

## [1.2.0] — 2026-09-23

### Changed

- **One executable instead of a folder.** Every product in this family now
  freezes to a single file; CLAUDE.md carries the rule and what it costs. An
  archive is the program, its launcher, its checksum and the licence texts —
  no `_internal/` to be told to leave alone. Nothing a spec file declares as
  data is visible after the build any more, because it is unpacked to a
  temporary directory while the program runs, so the workflow writes the
  things a reader has to be able to see beside the executable instead.

  It is slower to start: the executable unpacks about 60 MB on each launch,
  measured at four seconds cold and just over one warm on an ordinary Linux
  machine.

  **This changes how one licence obligation is met, and the documents say so.**
  A folder build answered LGPL-3.0 §4(d) by making every Qt library a file in
  the archive that a recipient could overwrite. There is no such file now, so
  §4(d)(1) is the route instead: published application source, the pinned Qt
  version, and a one-command rebuild. THIRD-PARTY-LICENSES.md sets it out, and
  §11 of COMMERCIAL-LICENSE.md says plainly that the route does not transfer
  to a closed derivative — that is a redistributor's own arrangement to make.

### Fixed

- **The per-platform inventory had never actually inventoried anything.** The
  release step read `build/P7MManager`, which is PyInstaller's work directory
  and holds no collected libraries in either build shape. On Linux that path
  does not even exist, because the work directory is named after the spec file
  and this one is lowercase, so the script died in `argparse` — which exits 2,
  the same code the inventory uses for "written, some rows need a human", so
  the step turned it into a warning and the archive shipped without the report
  §11 promises. It now reads `PKG-00.toc`, PyInstaller's own record of what
  went into the executable. That reader is not new: Iris, Proteus, Argus and
  Tyche have had it for a while and this repository, Orion and XIP were the
  three left on the older copy. It is the better witness besides — it carries
  the *source* path of every file, so a system library is resolved by where it
  came from rather than by matching a name dpkg may not recognise.

  The count drops from 201 to **184**, and the drop is the counting. Seventeen
  of Qt's libraries ship as `libQt6Foo.so.6` pointing at the real file beside
  it; walking a folder counts both, reading the build's record counts the
  library once. Reading the finished executable instead agrees with it exactly,
  which is the check worth having.
- **A step that writes no report now fails** instead of warning. An exit code
  cannot distinguish a mistyped path from rows needing review; the presence of
  the file can.
- **The macOS bundle claimed to be 1.0.0** two releases after it was. Nothing
  read `Info.plist` except Finder, so nothing noticed. A test holds it to the
  version the program reports.

## [1.1.0] — 2026-09-19

Alignment with the conventions the other six products in this family follow.

### Added

- **The third-party licence texts travel inside the archive.** Until now a
  release carried P7M Manager's own LICENSE, COMMERCIAL-LICENSE.md, README and
  CHANGELOG — and not one line of Qt's. That is not an untidiness: PySide6 is
  the only runtime dependency and therefore nearly the whole third-party
  surface of a build, and Qt is **LGPL-3.0**, whose §4 asks for the licence
  text to accompany the object code in as many words. The PySide6 wheels
  declare LGPL-3.0 and then ship no licence file at all, so the text is
  supplied from `licenses/` in this repository, together with GPL-3.0, because
  LGPL-3.0 is a set of additional permissions on top of it and means nothing
  alone. CPython's own notice goes in too: the interpreter and standard
  library are frozen into the bundle and PSF-2.0 asks for it.
- **A per-platform inventory of what the bundle contains**, generated on the
  machine that built it — the only one whose answer is that download's own,
  since PyInstaller collects whatever that linker resolved. A Linux build
  comes to 201 native binaries, all attributed. `tools/collect_licences.py`
  and `tools/licence_inventory.py` do it, and the release job runs the
  inventory with `--licences` so a distribution that ships a binary and no
  notice fails the job rather than shipping.
- **The terms of the system libraries the build machine contributes.** The
  licence tree is assembled from inside `p7mmanager.spec` now, because only
  the spec file has `a.binaries` — PyInstaller's record of what it actually
  resolved on that machine — and that list is the only route to them. Run as a
  separate step outside the build, which is how it started, the collector saw
  installed Python metadata and nothing else: it produced a tree covering the
  wheels while the archive carried eighty-odd system libraries with none of
  their licence files, twenty-one of them LGPL-2.0 or LGPL-2.1 whose §6 wants a
  copy of the licence with the object code — and §11 of COMMERCIAL-LICENSE.md
  promising the recipient exactly that. A Linux build's tree is 91 files, 83 of
  them those records.

### Changed

- **The dependency is `PySide6-Essentials`, not the `PySide6` metapackage.**
  The metapackage brings PySide6-Addons with it, and this program imports
  QtCore, QtGui and QtWidgets and nothing else. Addons was eighteen further Qt
  libraries in every archive, each of them an object carrying LGPL-3.0
  obligations, covering modules no line of code here can reach. A Linux build
  falls from 217 native binaries to 201.
- `THIRD-PARTY-LICENSES.md`, which the repository did not have.
- `tests/test_docs.py`, `tests/test_release_workflow.py` and
  `tests/test_third_party_licences.py` — the three shared guard suites P7M
  Manager was missing.
- `.gitattributes`, a pull-request template and an issue chooser.

### Fixed

- **`packaging/start.cmd` shipped with Unix line endings.** It is read by
  `cmd.exe`, it uses `goto` seven times, and `goto` with LF-only endings is
  the classic way a batch file fails in front of a user and nowhere else.
  Orion, XIP and Argus all ship theirs with CRLF; this one did not, and
  nothing pinned it. `.gitattributes` now does, for the file and for every
  checkout, and a test fails if either launcher's endings drift.
- Every job in both workflows declares a `timeout-minutes`. Without one they
  inherit GitHub's six-hour default, which is what a hung Qt test looks like
  from the outside: nothing, for an afternoon.
- Fifteen files under `tests/` and `tools/` carried a four-line licence header
  where the other thirty-three had five, missing the warranty disclaimer. All
  forty-eight are now identical.
- The README never linked `CLA.md`, though contributions require one.

### Changed

- The README follows the section skeleton the other products share, so a
  reader who has found something in one knows where to look here. The two
  sections that are P7M Manager's own — the privacy statement and what the
  tool does not claim — are kept, as subsections where they belong.
- **§11 of the commercial licence says what a redistributor actually
  receives**, now that it is true: the inventory, the licence tree, the
  obligations Qt and the LGPL system libraries carry, the GCC Runtime Library
  Exception, the Windows CRT, and the GPL-3 library the spec keeps out. It
  used to tell a redistributor to go and inventory the build themselves.

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
- **Privacy as a checked property, not a claim.** The documents never leave the machine
  because the application opens no network connections at all: `tests/test_privacy.py`
  fails if any networking module is ever imported, and runs a full analysis and extraction
  with sockets made unusable. The README says what is written to disk, so the list is
  complete.
- **Downloadable builds.** A release workflow builds a Windows executable, a macOS bundle
  and a Linux binary on their own runners, smoke-tests each one — `--self-check` brings up
  Qt and reports which platform plugin it loaded, because a bundle missing its plugin
  passes `--version` and then fails on a desktop — and attaches the three archives to the
  release for the tag. Their SHA-256 digests are written into the release notes rather than
  published as assets: a checksum has to arrive by a route the archive did not, and the
  page is such a route without putting three more files in a download list.
- **One shape for every download.** Each archive unpacks to a folder called `P7M Manager`
  holding the launcher, the executable, its checksum and the licence texts. The launcher
  verifies the program against that checksum before starting it — what catches a truncated
  download or a half-finished unpack — and refuses to start something that does not match;
  the release build proves both halves before publishing.
- **An application icon**: a serif `P` in a frame, black on white, the same drawing Orion
  uses for its `O`, so the products read as one family on a taskbar. Drawn by
  `tools/make_icon.py` into the `.ico`, `.icns` and `.png` a release needs, committed rather
  than generated at build time, and checked by a test that redraws them.
- **The name, the version and the copyright, on screen.** The title bar carries the tool
  and its version, the status bar carries the Appropriate Legal Notice AGPL-3.0 section 5
  asks for — copyright, licence and the address for commercial enquiries — and an About box
  adds the Python and Qt versions a bug report needs, alongside the limits of what the tool
  checks.
