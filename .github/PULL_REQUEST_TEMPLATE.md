## Description

<!-- What changes, and why. If it fixes a bug, describe the symptom you observed. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Improvement (performance, readability, interface)
- [ ] Documentation only

## Checks

- [ ] `pytest` passes (headless: `QT_QPA_PLATFORM=offscreen pytest`)
- [ ] No real `.p7m` was committed — fixtures are generated at collection time
- [ ] A bug fix comes with a test that fails without the change
- [ ] `CHANGELOG.md` updated under *Unreleased*
- [ ] Documentation updated if the behaviour changed
- [ ] `ruff check .` passes
- [ ] If the build or the dependencies were touched:
      `pyinstaller --noconfirm --clean p7mmanager.spec` run, and the bundle it produced
      started with `--self-check`
- [ ] I have read and agree to the Contributor License Agreement (CLA.md).

## Notes for the reviewer

<!-- What to look at, alternatives considered, known limitations. -->
