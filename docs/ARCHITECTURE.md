# Architecture

How P7M Manager is put together, and why. Read this before a change larger than a bug fix.

---

## 1. The shape of the thing

```
p7mmanager/
├── core/            the engine — no Qt, ever
│   ├── asn1.py      BER/DER reader
│   ├── oids.py      the object identifiers this tool recognises
│   ├── x509.py      certificates
│   ├── cms.py       SignedData: signers, attributes, timestamps
│   ├── verify.py    integrity and RSA signature checks
│   ├── payload.py   what came out of the envelope, and what to call it
│   ├── analyzer.py  one file in, one Analysis out
│   ├── extractor.py writing the document, atomically
│   ├── scanner.py   files and folders in, a list of containers out
│   ├── jobs.py      the execution queue
│   └── report.py    CSV and JSON
├── ui/              PySide6 — owns no parsing logic
│   ├── main_window.py
│   ├── queue_model.py
│   └── details.py
├── utils/           paths, logging, settings — no Qt either
├── i18n.py          English source strings, Italian from a table
├── cli.py           the console tool
└── main.py          entry point
```

The rule that shapes everything else: **`core/` never imports Qt**, and
`tests/test_project.py` fails if it ever does. The window, the command line and the tests
are three callers of one engine, and the engine can be exercised without a display.

## 2. Why the ASN.1 reader is in this repository

A signed container is ASN.1, and there are good libraries for it. This project writes its
own anyway, for three reasons:

1. **Deployment.** The people who most need this tool run it on a managed corporate desktop
   where `pip install cryptography` is somewhere between awkward and forbidden. A pure
   standard-library engine runs on a plain Python install, and on a frozen build with
   nothing to compile.
2. **Licensing.** P7M Manager is dual-licensed. A copyleft dependency underneath the parser
   would limit what a Redistribution customer actually receives — the problem MuPDF caused
   in Orion until it was replaced. The engine's dependency list is empty on purpose; see
   §11 of `COMMERCIAL-LICENSE.md`.
3. **Scope.** Reading a `SignedData` and an X.509 certificate is a bounded problem, and it
   is the whole of what this tool does. Verifying an RSA PKCS#1 v1.5 signature is
   `pow(signature, e, n)` plus a padding check — around forty lines, and testable against
   containers OpenSSL produced.

What that rules out is stated rather than hidden: no ECDSA, no RSA-PSS, no trust chain, no
revocation, no timestamp validation. Each is reported as unchecked, never as valid.

### 2.1 BER, not just DER

CAdES files in the wild are not always DER. Some signing devices emit indefinite lengths
and segmented octet strings, so the reader handles both, and `Node.octets()` joins the
segments. A parser that accepted only DER would reject real, valid signatures.

## 3. One file, one `Analysis`

`analyzer.analyse(path)` is the engine's front door, and it **never raises** for a bad
file: every failure — unreadable, too large, not CMS, damaged — becomes a field on the
returned `Analysis`. A queue of five hundred containers must not stop at the first one
somebody truncated.

The same function handles the shapes a container arrives in:

- raw DER, the normal case;
- base64, with or without PEM banners, as several PEC providers deliver it;
- an envelope whose payload is another envelope, unwrapped up to `MAX_NESTING`;
- a detached signature, which parses fine and simply has nothing to extract;
- a file too damaged to parse, where an embedded PDF is carved out of the bytes instead —
  the behaviour of the shell scripts this tool replaces, kept as a last resort and flagged
  in the result, because nothing about such a file's signature was verified.

## 4. What verification claims

Two questions, deliberately kept apart because users act on them differently:

| Field | Question | How |
|---|---|---|
| `digest_matches` | Is the document the one that was signed? | Hash the enclosed content, compare with the `messageDigest` signed attribute |
| `signature_valid` | Did this certificate's key produce this signature? | RSA PKCS#1 v1.5 over the DER of the signed attributes, re-tagged as a `SET OF` |

`None` means *not checked* and is never rendered as a pass. The wording in `ui/details.py`,
in the CLI and in the reports is part of the contract: see the section on it in `CLAUDE.md`.

## 5. The queue

`jobs.JobQueue` is a `ThreadPoolExecutor` over the file list. The work is I/O and hashing,
so threads are right; cancellation is cooperative and checked between files, never mid
write, so a cancelled run never leaves a partial document.

The queue reports what it does by calling a listener **from worker threads**. It does not
know what the listener is. The window passes `queue.Queue.put` and drains that queue from a
`QTimer` on the GUI thread, which is the one place thread affinity has to be right; the CLI
passes nothing and simply waits. Widgets are never touched from a worker.

## 6. Writing the document

`extractor.extract` writes to a temporary file in the destination folder and `os.replace`s
it into position, so an interrupted or failing write leaves either the complete file or
nothing at all.

The container is opened read-only and never modified, moved or deleted — including when the
extracted name would collide with it.

The output name comes from the container's own name when it already carries the inner
extension (`fattura.xml.p7m` → `fattura.xml`), because that is the name the sender chose,
and from the detected content type only when it does not (`allegato.p7m` → `allegato.pdf`).

## 7. Language

English is the source language; `i18n.tr` looks the Italian up in a dict. `QTranslator` was
not chosen for the same reason Orion did not choose it: a `.qm` is a binary blob built by a
separate tool, and a missing translation in one is silent. Here, `tests/test_i18n.py` walks
the source for every `tr(...)` call and fails on any phrase with no Italian.

Engine messages are English too, and arrive with a variable tail — `read failed: Permission
denied`. `tr_message` translates the fixed part and leaves the system's own words alone.

## 8. Settings, logs, paths

`utils/paths.py` is the only module that branches on the platform. `P7MMANAGER_HOME`
overrides all of it, which is what the tests set and what a portable install wants.
Settings are one JSON file; an unreadable one is replaced by defaults rather than stopping
the application.

## 9. What is deliberately absent

- **No trust store, no CRL/OCSP, no TSA calls.** All three need network access and a policy
  decision about whom to trust, and all three would turn "this file is intact" into a claim
  about legal validity that this tool does not make.
- **No signing.** Reading is a bounded problem; producing signatures is not, and it needs a
  smartcard stack.
- **No decryption.** `envelopedData` is recognised and named in the error, nothing more.
- **No document rendering.** The extracted file is handed to the system's own viewer.
