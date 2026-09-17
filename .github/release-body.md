**P7M Manager {{VERSION}}** — inspect signed `.p7m` containers and extract the documents
they carry. Download the build for your platform below; nothing needs installing, and
nothing phones home.

| Platform | Download | How to run it |
|---|---|---|
| **Windows** (x64) | `P7MManager-{{VERSION}}-windows-x64.zip` | Unzip anywhere, run `P7MManager.exe`. Windows SmartScreen will warn about an unsigned application: *More info → Run anyway*. |
| **macOS** (Apple silicon) | `P7MManager-{{VERSION}}-macos-arm64.zip` | Unzip, move `P7MManager.app` to Applications. The bundle is unsigned: first launch is *right-click → Open*, or `xattr -dr com.apple.quarantine P7MManager.app`. |
| **Linux** (x64) | `P7MManager-{{VERSION}}-linux-x64.tar.gz` | Extract and run `./P7MManager`. Needs the usual Qt libraries: `libegl1 libgl1 libxkbcommon0 libfontconfig1`. |

Each archive carries the licence texts and this version's `README.md`. The builds are
unsigned — there is no code-signing certificate behind this project — so every platform
will say so the first time.

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
