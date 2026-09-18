**P7M Manager {{VERSION}}** — inspect signed `.p7m` containers and extract the documents
they carry. Download the build for your platform below; nothing needs installing, and
nothing phones home.

| Platform | Download | How to run it |
|---|---|---|
| **Windows** (x64) | `P7MManager-{{VERSION}}-windows-x64.zip` | Unzip, open the `P7M Manager` folder, run **`start.cmd`**. SmartScreen will warn about an unsigned application: *More info → Run anyway*. |
| **macOS** (Apple silicon) | `P7MManager-{{VERSION}}-macos-arm64.zip` | Unzip, open the `P7M Manager` folder, run **`start.command`**. The bundle is unsigned: first launch is *right-click → Open*. |
| **Linux** (x64) | `P7MManager-{{VERSION}}-linux-x64.tar.gz` | Extract, `cd "P7M Manager"`, run **`./start.sh`**. Needs the usual Qt libraries: `libegl1 libgl1 libxkbcommon0 libfontconfig1`. |

Every archive unpacks to one folder, `P7M Manager`, holding the launcher, the executable,
its checksum and the licence texts. **Run the launcher, not the executable**: it verifies
the program against the checksum shipped beside it and refuses to start something that does
not match — which catches a truncated download or a half-finished unpack. Arguments pass
straight through, so `start.cmd --cli documenti -r` works too.

To check the download itself, the SHA-256 of each archive is at the bottom of this page.
It reaches you by a different path from the archive, which is the point — a replaced
download cannot quietly carry a matching digest.

The builds are unsigned — there is no code-signing certificate behind this project — so
every platform will say so the first time. Nothing in a release can remove that warning;
only a certificate can.

Prefer to run from source, or want the command line on a server?

```
pip install "p7m-manager @ git+https://github.com/MarcoLombardoDev/P7MManager@{{TAG}}"
p7mmanager          # the window
p7m --help          # the console tool
```

### What it checks, and what it does not

It verifies that the enclosed document still matches the digest the signature covers and,
for RSA, that the signature was produced by the enclosed certificate's key.

**This is not a legal validation.** There is no trust list, no revocation check and no
timestamp validation, so nothing the tool reports says whether a signature is legally
valid. Where a legal determination is needed, use an accredited validation service.

### Licence

Free software under [AGPL-3.0-or-later](https://github.com/MarcoLombardoDev/P7MManager/blob/{{TAG}}/LICENSE).
Using it inside your organisation is free, at any size. A
[commercial licence](https://github.com/MarcoLombardoDev/P7MManager/blob/{{TAG}}/COMMERCIAL-LICENSE.md)
covers closed-source internal use and redistribution.

Full notes: [CHANGELOG.md](https://github.com/MarcoLombardoDev/P7MManager/blob/{{TAG}}/CHANGELOG.md)
