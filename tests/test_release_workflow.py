# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Tests for .github/workflows/release.yml and .github/release-body.md.

GitHub Actions is the only thing that can actually run the workflow, so these
tests parse the checked-in files instead. They exist because every bug they
guard against has already been shipped once, in one of the sibling projects
that share this release machinery:

- a release published with no title, showing only the bare tag;
- notes produced by ``--generate-notes``, which dumps the commit log — for a
  first release, the entire project history — where a description of what is
  being downloaded should be;
- a release created through GitHub's own "Draft a new release" page, which
  makes ``gh release create`` fail, leaving the fallback path to publish a
  release with whatever title the web UI defaulted to;
- a download table promising macOS and Linux builds that the workflow never
  actually built.
"""

from pathlib import Path

# A hard import, not pytest.importorskip. The skip was there from when PyYAML
# was an optional convenience, and it outlived that: PyYAML is declared in this
# repository's development dependencies, so a run without it is a broken
# environment, not a lighter one. Meanwhile the skip was doing real damage --
# 35 of the checks below parse the release workflow, and on a runner that had
# not installed PyYAML they reported nothing at all and the suite finished
# green. Guards on the file that publishes the releases were the guards not
# being run, and nothing said so. Missing now fails at collection.
import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO / ".github" / "workflows" / "release.yml"
BODY_PATH = REPO / ".github" / "release-body.md"

#: Two names, unlike every other product in this family, which have one.
#: BUNDLE_NAME is what PyInstaller writes, what the executable is called and
#: what the archives are named — it has no space, because it is also typed at
#: a prompt. APP_NAME is the product, and it is what the archive unpacks to,
#: because that is the folder somebody ends up with on their desktop.
APP_NAME = "P7M Manager"
BUNDLE_NAME = "P7MManager"
SKIP_VERIFY = "P7MMANAGER_SKIP_VERIFY"

#: The step that assembles what goes in the archive. Named for everything it
#: does here, because unlike the other products this one also copies the
#: licence tree in.
LAUNCHER_STEP = "Add the launcher, the licences and their checksum"

#: Every platform the release promises. Each must be genuinely built, on its
#: own runner: PyInstaller does not cross-compile, so a missing runner means a
#: missing binary, not a slower one.
PLATFORMS = {
    "windows-latest": "windows-x64",
    "macos-latest": "macos-arm64",
    "ubuntu-latest": "linux-x64",
}


def load_workflow():
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def triggers(workflow):
    # PyYAML's 1.1 reader parses the bare ``on:`` key as the boolean True.
    # That is a quirk of the library, not of the workflow file.
    return workflow.get("on") or workflow[True]


def build_steps(workflow):
    return workflow["jobs"]["build"]["steps"]


def step_named(steps, name):
    return next((step for step in steps if step.get("name") == name), None)


def test_the_workflow_is_valid_yaml_and_has_all_three_jobs():
    workflow = load_workflow()
    assert set(workflow["jobs"]) == {"release", "build", "checksums"}


def test_every_workflow_file_in_the_repository_parses():
    """A broken workflow file fails silently: GitHub simply never shows the
    run. Catching the syntax error here is much cheaper than noticing its
    absence on the Actions tab.
    """
    for path in (REPO / ".github" / "workflows").iterdir():
        if path.suffix in (".yml", ".yaml"):
            assert yaml.safe_load(path.read_text(encoding="utf-8")), path.name


def test_every_job_declares_a_timeout():
    """A job without one runs until GitHub's own six-hour limit.

    Nothing here has ever hung — every run finishes in about three minutes —
    but if one did, it would look like a very slow build and say nothing, for
    hours. Asserted across both workflows so a job added later cannot quietly
    arrive without one.
    """
    for path in sorted((REPO / ".github" / "workflows").iterdir()):
        if path.suffix not in (".yml", ".yaml"):
            continue
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name, job in (workflow.get("jobs") or {}).items():
            timeout = job.get("timeout-minutes")
            assert timeout, f"{path.name}: job {name!r} has no timeout-minutes"
            assert timeout <= 60, (
                f"{path.name}: job {name!r} may run for {timeout} minutes, which "
                "is long enough for a hang to look like work"
            )


def test_all_three_platforms_are_built_on_their_own_runner():
    matrix = load_workflow()["jobs"]["build"]["strategy"]["matrix"]["include"]
    built = {entry["os"]: entry["asset"] for entry in matrix}
    assert built == PLATFORMS


def test_one_platform_failing_does_not_cancel_the_others():
    """fail-fast would throw away a good Windows build because macOS broke."""
    assert load_workflow()["jobs"]["build"]["strategy"]["fail-fast"] is False


def test_the_workflow_can_be_triggered_by_hand_and_by_a_tag():
    on = triggers(load_workflow())
    assert "workflow_dispatch" in on
    assert on["push"]["tags"] == ["v*"]


def test_publishing_a_release_does_not_start_a_second_racing_run():
    """Regression, seen live on Proteus v1.3.0: with a "release: published"
    trigger alongside the tag's push trigger, publishing a release from
    GitHub's UI fires both — the UI creates the tag, which is itself a push.
    Two runs then built the same three archives at once and uploaded them over
    each other with --clobber. The tag's push event covers both routes, so it
    is the only one kept.
    """
    assert "release" not in triggers(load_workflow())


def test_the_workflow_can_write_repository_contents():
    """Without this, `gh release create` fails on any repo or organisation
    that has tightened the default GITHUB_TOKEN to read-only.
    """
    assert load_workflow()["permissions"]["contents"] == "write"


def test_the_app_name_matches_this_product():
    """The packaging and upload steps are driven entirely by APP_NAME; a stale
    one silently produces archives nobody is looking for.
    """
    env = load_workflow()["env"]
    assert env["APP_NAME"] == BUNDLE_NAME
    assert env["FOLDER_NAME"] == APP_NAME


def test_every_bundle_is_smoke_tested_before_it_is_offered_for_download():
    """A bundle that cannot start is worse than no bundle."""
    step = step_named(build_steps(load_workflow()), "Smoke-test the bundle")
    assert step is not None, "no smoke-test step in the build job"
    assert "--version" in step["run"]


def test_the_smoke_test_actually_starts_qt():
    """--version on its own proves nothing about Qt.

    argparse's version action prints and exits inside argument parsing, before
    PySide6 is imported at all. A bundle missing its Qt platform plugin passes
    ``--version`` and then fails the moment a user double-clicks it. The smoke
    test has to construct a QApplication, which is what makes Qt go looking for
    a plugin, and it has to check which one it found.
    """
    step = step_named(build_steps(load_workflow()), "Smoke-test the bundle")
    assert "--self-check" in step["run"], (
        "the smoke test never starts Qt, so it cannot detect a broken bundle"
    )
    assert "platform plugin" in step["run"], (
        "the smoke test does not check which platform plugin was loaded"
    )


def test_the_linux_smoke_test_uses_a_real_display_not_offscreen():
    """offscreen loads none of the X libraries.

    A Linux bundle with a broken or unshippable xcb plugin comes up perfectly
    under QT_QPA_PLATFORM=offscreen — which is precisely the failure the smoke
    test exists to catch. It has to run against a virtual X server and the
    real backend.
    """
    step = step_named(build_steps(load_workflow()), "Smoke-test the bundle")
    assert "xvfb-run" in step["run"]
    assert "QT_QPA_PLATFORM=xcb" in step["run"]
    assert "Linux:xcb" in step["run"], "no assertion that xcb is what came up"


def test_the_virtual_x_server_is_installed_on_the_linux_runner():
    """A smoke test that calls xvfb-run without xvfb fails the release."""
    step = step_named(
        build_steps(load_workflow()), "Install the platform's system libraries"
    )
    assert step is not None
    assert "xvfb" in step["run"]


def test_the_smoke_test_runs_before_packaging():
    steps = [step.get("name") for step in build_steps(load_workflow())]
    assert steps.index("Smoke-test the bundle") < steps.index("Package")


def test_the_release_notes_come_from_the_repository_not_from_the_commit_log():
    step = step_named(
        load_workflow()["jobs"]["release"]["steps"], "Create or update the release"
    )
    assert step is not None
    assert "--generate-notes" not in step["run"]
    assert ".github/release-body.md" in step["run"]


def test_the_release_gets_a_title_on_both_paths():
    """`gh release create` fails outright when a release already exists for the
    tag — which is the normal case for the "release published" trigger, and for
    anything drafted through GitHub's own UI. The fallback has to set the title
    and notes too, or the run "succeeds" leaving a blank release behind.
    """
    step = step_named(
        load_workflow()["jobs"]["release"]["steps"], "Create or update the release"
    )
    run = step["run"]
    assert "gh release create" in run
    assert "gh release edit" in run
    assert "--draft=false" in run, "a draft release is invisible to anonymous visitors"
    assert run.count("--title") == 2 and run.count("--notes") == 2


def test_assets_from_a_previous_build_are_removed_first():
    """Moving a tag onto a new commit leaves the old release's assets in place.
    They are not overwritten by name — the archives are named after the
    platform and the version — so an abandoned file would sit under notes that
    no longer describe it, offering a download nobody built.
    """
    steps = load_workflow()["jobs"]["release"]["steps"]
    step = step_named(steps, "Remove assets left by a previous build")
    assert step is not None, "no stale-asset cleanup step in the release job"
    assert "gh release delete-asset" in step["run"]

    names = [s.get("name") for s in steps]
    assert names.index("Create or update the release") < names.index(
        "Remove assets left by a previous build"
    ), "the release has to exist before its assets can be listed"


def test_only_version_tags_are_accepted():
    step = step_named(load_workflow()["jobs"]["release"]["steps"], "Work out which tag to build")
    assert "v[0-9]*" in step["run"], "a non-version tag must not publish a release"


def test_the_download_table_lists_exactly_what_is_built():
    """Regression: the notes used to promise macOS and Linux downloads that no
    job ever produced.
    """
    body = BODY_PATH.read_text(encoding="utf-8")
    for asset in PLATFORMS.values():
        extension = "tar.gz" if asset.startswith("linux") else "zip"
        expected = BUNDLE_NAME + "-{{VERSION}}-" + asset + "." + extension
        assert expected in body, asset


def test_the_release_body_carries_the_version_and_tag_placeholders():
    """They are substituted by the workflow; a literal placeholder reaching the
    published notes means the substitution stopped matching.
    """
    body = BODY_PATH.read_text(encoding="utf-8")
    assert "{{VERSION}}" in body
    assert "{{TAG}}" in body


def test_the_release_body_points_at_the_licence_and_the_commercial_terms():
    body = BODY_PATH.read_text(encoding="utf-8")
    assert "AGPL-3.0" in body
    assert "COMMERCIAL-LICENSE.md" in body


def test_the_bundle_is_inventoried_on_the_machine_that_built_it():
    """A hand-written list of a PyInstaller bundle is wrong the day after.

    PyInstaller collects whatever the runner's linker resolved, so the
    contents change when the image changes, not when anybody edits this
    repository. The inventory therefore has to be generated per build and
    travel with the archive it describes.
    """
    step = step_named(build_steps(load_workflow()), "Inventory what the bundle ships")
    assert step is not None, "nothing inventories the bundle"
    run = step["run"]
    assert "tools/licence_inventory.py" in run
    assert "--markdown" in run and "THIRD-PARTY-LICENSES-" in run


def test_the_inventory_reads_what_the_build_packed():
    """A onefile build leaves no directory to inventory.

    The libraries go inside the executable and are unpacked to a temporary
    directory only while it runs, so what is read is PyInstaller's own record
    of the build: ``Analysis-00.toc`` in the work directory, which also carries
    where each file came from.

    The path is lowercase because PyInstaller names that directory after the
    spec file. It used to be spelled ``build/$APP_NAME``, which resolves on a
    case-insensitive filesystem and does not exist on Linux, so the script died
    in argparse there.
    """
    run = step_named(build_steps(load_workflow()), "Inventory what the bundle ships")["run"]
    assert "=build/p7mmanager" in run, "the inventory is not reading the build's own record"
    assert "=build/$APP_NAME" not in run, (
        "back to a path that does not exist on a case-sensitive filesystem"
    )


def test_an_inventory_that_writes_no_report_fails_the_build():
    """The hole that let the above ship for three releases.

    ``argparse`` exits 2 on a bad argument. An inventory that wrote its report
    and wants a human to read some rows also exits 2. The case statement below
    maps 2 to ``::warning::``, so a mistyped path arrived as a warning nobody
    reads and the archive went out without the inventory §11 promises.

    An exit code cannot tell those apart. The report file can.
    """
    run = step_named(build_steps(load_workflow()), "Inventory what the bundle ships")["run"]
    assert '[ ! -s "$report" ]' in run, (
        "nothing checks that a report was actually written"
    )
    assert "exit 1" in run


def test_the_inventory_is_written_where_the_archive_will_carry_it():
    """Into the licence tree, not to some path of its own.

    The packaging step copies `build/licenses` into the archive wholesale, so
    a report written anywhere else is a report nobody who downloads this ever
    sees — which is the whole point of generating it on the runner.
    """
    steps = build_steps(load_workflow())
    inventory = step_named(steps, "Inventory what the bundle ships")
    assert "build/licenses/THIRD-PARTY-LICENSES-" in inventory["run"]

    packaged = step_named(steps, LAUNCHER_STEP)
    assert "cp -R build/licenses" in packaged["run"], (
        "the tree the report was written into never reaches the archive"
    )


def test_the_inventory_runs_against_the_bundle_that_ships():
    """Not against the source tree, and not against an installed copy: the
    question is what *this* archive contains."""
    run = step_named(build_steps(load_workflow()), "Inventory what the bundle ships")["run"]
    assert "--bundle" in run
    assert "build/$APP_NAME" in run, "the inventory is not pointed at the build output"


def test_an_unattributed_binary_warns_rather_than_failing_the_release():
    """Blocking a release on an unresolved row would only encourage guessing.

    The report already says "unresolved", which is the honest answer; what is
    needed is that somebody sees it.
    """
    step = step_named(build_steps(load_workflow()), "Inventory what the bundle ships")
    assert "::warning::" in step["run"]


def test_a_crashing_inventory_fails_the_step_rather_than_warning():
    """A release run once shipped two archives with no inventory in them.

    The script raised on every machine without dpkg — which is every Windows
    and macOS runner — and `|| echo "::warning::"` turned the crash into a
    warning nobody reads. Exit 1 cannot be the signal for "some rows need a
    human", because an uncaught Python exception exits 1 as well; the script
    uses 2 for that, and anything else has to fail the step.
    """
    step = step_named(build_steps(load_workflow()), "Inventory what the bundle ships")
    assert "::error::" in step["run"], (
        "nothing distinguishes a crash from an unattributed binary, so a crash "
        "publishes an archive with no inventory in it"
    )
    assert "2)" in step["run"], "the warning is not tied to the script's own exit code"
    assert 'exit "$status"' in step["run"]


def test_the_inventory_also_checks_that_every_wheel_got_its_notice():
    """The two halves of the licence work have to agree with each other.

    The inventory says which distributions put a binary in the archive; the
    collector says whose terms travel with it, from a list kept by hand. A
    dependency that starts shipping a native extension is attributed happily by
    the first and missed entirely by the second, and nothing compared them.
    """
    step = step_named(build_steps(load_workflow()), "Inventory what the bundle ships")
    assert "--licences" in step["run"], (
        "nothing checks that a binary's licence text is in the archive with it"
    )

class TestSelfCheck:
    """``--self-check`` is what makes a bundle verifiable, and ``--version``
    is not.

    argparse prints the version and exits before PySide6 is ever imported, so
    a bundle whose Qt platform plugin was never collected passes ``--version``
    and then fails on the user's desktop. ``--self-check`` constructs a
    QApplication, which is what makes Qt load a platform plugin, and reports
    which one it got.

    Two lines, the second in a fixed ``key: value`` shape, because the release
    workflow greps it. That grep and this test are the two ends of the same
    contract: change the wording in ``p7mmanager/main.py`` and this fails.
    """

    def source(self) -> str:
        return (REPO / "p7mmanager" / "main.py").read_text(encoding="utf-8")

    def test_it_is_a_real_flag(self):
        assert '"--self-check"' in self.source()

    def test_it_constructs_qt_rather_than_only_importing_it(self):
        """Importing PySide6 proves the wheel is in the bundle. It does not
        prove Qt can start, which is the thing that breaks."""
        source = self.source()
        assert "QApplication(" in source
        assert "platformName()" in source

    def test_it_prints_the_platform_plugin_in_the_shape_the_workflow_greps(self):
        assert 'f"platform plugin: {app.platformName()}"' in self.source()

    def test_the_workflow_greps_for_exactly_that(self):
        text = "\n".join(s.get("run", "") for s in build_steps(load_workflow()))
        assert "platform plugin:" in text, (
            "the workflow no longer reads the line --self-check exists to print"
        )

    def test_it_exits_before_building_a_window(self):
        """A self-check that opened the interface would need a human to close
        it, and the release job has none."""
        source = self.source()
        check = source.index("if args.self_check:")
        window = source.index("MainWindow()")
        assert check < window, "--self-check runs after the window is built"
        assert "return 0" in source[check:window]


class TestChecksums:
    """What an unsigned build can offer in place of a signature.

    Windows tells whoever downloads one of these that the publisher is
    unknown, and it is right: there is no code-signing certificate. Nothing in
    this repository can change that. What it can do is answer the question the
    warning raises — is this the file the build produced? — and that answer is
    a checksum published beside the archive.

    It is weaker than a signature and it is not nothing: it covers everything
    between the build machine and the user's disk.
    """

    def test_every_archive_gets_a_checksum(self):
        step = step_named(build_steps(load_workflow()), "Record the checksum")
        assert step is not None, "the archives ship with nothing to check them against"
        assert "sha256" in step["run"].lower()

    def test_the_checksum_leaves_the_runner(self):
        """A checksum that stays on the runner is a checksum nobody has. It is
        no longer a release asset — three extra files in a download list of
        three is noise — so it travels up as a workflow artifact instead, and
        the job at the end writes it into the notes.
        """
        steps = build_steps(load_workflow())
        step = step_named(steps, "Hand the checksum to the notes job")
        assert step is not None, "the digest never leaves the build runner"
        assert step["with"]["path"].endswith(".sha256")
        assert step["with"]["if-no-files-found"] == "error", (
            "a missing digest would pass silently"
        )

    def test_the_checksums_are_not_release_assets(self):
        """What the download list offers is three archives, not six files."""
        step = step_named(build_steps(load_workflow()), "Upload to the release")
        assert ".sha256" not in step["run"]

    def test_the_checksums_reach_the_release_notes(self):
        """A checksum is worth something only if it arrives by a route the
        archive did not. The notes GitHub renders are such a route; a file
        inside the archive is not.
        """
        job = load_workflow()["jobs"]["checksums"]
        assert job["needs"] == ["release", "build"], (
            "a partial list of checksums is worse than none"
        )
        run = " ".join(step.get("run", "") for step in job["steps"])
        assert "gh release edit" in run
        assert "--notes-file" in run

    def test_rewriting_the_notes_twice_does_not_stack_two_blocks(self):
        """Re-running the release is normal. Appending a second checksum
        block each time is not.
        """
        job = load_workflow()["jobs"]["checksums"]
        run = " ".join(step.get("run", "") for step in job["steps"])
        assert "<!-- checksums -->" in run and "<!-- /checksums -->" in run

    def test_it_is_recorded_after_packaging(self):
        """The checksum describes the archive, so the archive has to exist."""
        names = [step.get("name") for step in build_steps(load_workflow())]
        assert names.index("Package") < names.index("Record the checksum")
        assert names.index("Record the checksum") < names.index("Upload to the release")

    def test_the_cleanup_removes_checksums_left_by_an_older_build(self):
        """v1.0.0 published its checksums as assets. A release the tag is
        moved onto still carries them, and the cleanup's job is to take away
        anything the notes no longer describe.
        """
        steps = load_workflow()["jobs"]["release"]["steps"]
        step = step_named(steps, "Remove assets left by a previous build")
        keep = step["run"].split("for name in", 1)[0]
        assert "$asset.sha256" not in keep, (
            "a checksum published by an older build would be kept for ever"
        )

    def test_it_is_written_in_the_format_a_tool_can_check(self):
        """`sha256sum -c` reads "<hex>  <name>". Anything else has to be
        compared by eye, which is how a wrong hash gets approved.
        """
        step = step_named(build_steps(load_workflow()), "Record the checksum")
        assert "{digest}  {archive.name}" in step["run"]


def test_the_download_notes_say_what_the_windows_warning_is():
    """An unsigned build makes Windows say the publisher is unknown, and a
    reader who was not told that reasonably concludes the download is bad.

    The checksums themselves are not in this file: the job at the end of the
    workflow writes them in, because a digest is only worth something if it
    arrives by a route the archive did not. What the static body has to do is
    prepare the reader for the warning and for the check.
    """
    body = BODY_PATH.read_text(encoding="utf-8")
    lowered = body.lower()
    assert "smartscreen" in lowered, "nothing warns the reader about the warning"
    assert "unsigned" in lowered
    assert "checksum" in lowered, "the notes never mention the check at all"


class TestLauncher:
    """The start script that ships next to the executable.

    A download that arrives truncated, or an unpack that stops half way,
    produces an executable that starts and then misbehaves in ways nobody can
    diagnose. The launcher turns that into one sentence at the point of
    launch, by comparing the executable against the digest recorded when it
    was built.

    It is careful about what it claims. The digest travels inside the same
    archive as the executable it describes, so it catches damage and not
    tampering — anyone who could replace one could replace the other. The
    check that answers *that* question is on the archive itself, against the
    ``.sha256`` published separately on the release page.
    """

    def test_both_launchers_are_in_the_repository(self):
        for name in ("start.sh", "start.cmd"):
            assert (REPO / "packaging" / name).is_file(), f"packaging/{name} is missing"

    def test_the_launcher_is_installed_beside_the_executable(self):
        """Not through the spec file: everything a spec declares as ``datas``
        is packed inside the executable and unpacked to a temporary directory
        while it runs, which is the one place a launcher is no use at all.
        Only the workflow can write next to the executable.
        """
        step = step_named(build_steps(load_workflow()), LAUNCHER_STEP)
        assert step is not None, "nothing puts a start script in the bundle"
        assert "packaging/start.cmd" in step["run"]
        assert "packaging/start.sh" in step["run"]

    def test_the_executable_gets_its_own_checksum_in_the_bundle(self):
        step = step_named(build_steps(load_workflow()), LAUNCHER_STEP)
        assert "sha256" in step["run"]
        assert ".exe.sha256" in step["run"], "no checksum beside the Windows exe"
        assert ".sha256" in step["run"]

    def test_that_checksum_is_written_where_a_tool_can_read_it(self):
        """``<hex>  <name>`` is what ``sha256sum -c`` reads. Any other shape
        has to be compared by eye, which is how a wrong digest gets waved
        through.
        """
        step = step_named(build_steps(load_workflow()), LAUNCHER_STEP)
        assert "{digest}  {name}" in step["run"]

    def test_the_launcher_is_added_before_the_archive_is_made(self):
        names = [step.get("name") for step in build_steps(load_workflow())]
        assert names.index(LAUNCHER_STEP) < names.index("Package")

    def test_the_archive_is_made_from_what_the_launcher_step_produced(self):
        """macOS moves the .app into a folder so the launcher has somewhere to
        sit beside it. Packaging the pre-move path would ship an archive with
        no launcher in it and nobody would notice until it was downloaded.
        """
        step = step_named(build_steps(load_workflow()), "Package")
        assert "steps.launcher.outputs.payload" in step["env"]["PAYLOAD"]

    def test_the_launcher_is_run_before_the_archive_is_made(self):
        """A launcher nobody started is a launcher nobody knows works."""
        names = [step.get("name") for step in build_steps(load_workflow())]
        assert "Start the bundle through the launcher" in names
        assert names.index("Start the bundle through the launcher") < names.index("Package")

    def test_the_release_run_proves_the_launcher_refuses_a_bad_checksum(self):
        """Checking that it starts the program proves half of it. A launcher
        that verifies nothing also passes that half.
        """
        step = step_named(build_steps(load_workflow()), "Start the bundle through the launcher")
        run = step["run"]
        assert "checksum did not match" in run, (
            "nothing checks that the launcher can refuse"
        )

    def test_the_launcher_refuses_rather_than_warning(self):
        script = (REPO / "packaging" / "start.sh").read_text(encoding="utf-8")
        body = script.split("digest_of()", 1)[1]
        assert "exit 1" in body, "the launcher does not stop on a mismatch"

    def test_the_launcher_can_be_told_to_skip_the_check(self):
        """Somebody who has patched the executable on purpose should be able
        to run it. The point is that they have to say so.
        """
        for name in ("start.sh", "start.cmd"):
            text = (REPO / "packaging" / name).read_text(encoding="utf-8")
            assert SKIP_VERIFY in text

    def test_the_launcher_passes_arguments_through(self):
        """``--version`` and ``--self-check`` are how the release itself
        starts the bundle. A launcher that swallowed them could not be tested
        by running it.
        """
        assert '"$exe" "$@"' in (REPO / "packaging" / "start.sh").read_text(encoding="utf-8")
        assert '"%EXE%" %*' in (REPO / "packaging" / "start.cmd").read_text(encoding="utf-8")

    def test_the_batch_launcher_keeps_windows_line_endings(self):
        """cmd.exe has historically mis-parsed ``goto`` in an LF-only batch
        file. ``.gitattributes`` pins it so no checkout can undo it.
        """
        raw = (REPO / "packaging" / "start.cmd").read_bytes()
        assert b"\r\n" in raw
        assert raw.replace(b"\r\n", b"") .count(b"\n") == 0, "mixed line endings"
        attrs = (REPO / ".gitattributes").read_text(encoding="utf-8")
        assert "*.cmd text eol=crlf" in attrs

    def test_the_shell_launcher_keeps_unix_line_endings(self):
        """/bin/sh treats a trailing CR as part of the last word, so a CRLF
        checkout produces "bad interpreter" and nothing else.
        """
        assert b"\r" not in (REPO / "packaging" / "start.sh").read_bytes()
        assert "*.sh text eol=lf" in (REPO / ".gitattributes").read_text(encoding="utf-8")

    def test_every_goto_in_the_batch_launcher_has_a_label(self):
        """cmd.exe does not check labels until it reaches the jump, so a
        `goto` at a branch nobody takes in testing fails in front of the user
        and nowhere else.
        """
        import re

        text = (REPO / "packaging" / "start.cmd").read_text(encoding="utf-8")
        labels = set(re.findall(r"^:(\w+)", text, re.MULTILINE))
        jumps = set(re.findall(r"\bgoto\s+:?(\w+)", text))
        assert jumps <= labels, f"goto with no label: {sorted(jumps - labels)}"

    def test_the_batch_launcher_says_something_while_the_program_starts(self):
        """A frozen Qt application can take most of a minute to appear the
        first time, because Windows scans the whole folder before it will run
        any of it. A console that closes instantly leaves the user watching an
        empty desktop with no idea whether anything happened.
        """
        text = (REPO / "packaging" / "start.cmd").read_text(encoding="utf-8")
        assert "echo Starting %APP%" in text

    def test_the_batch_launcher_waits_for_a_real_window(self):
        """It waits for a window to exist, by polling every process with the
        program's image name for a main window handle.

        Not WaitForInputIdle on the process Start-Process returned, which is
        what it did first and is wrong for a onefile build: the executable
        that starts is a bootloader that re-runs itself, the child draws the
        window, and the bootloader never has a message loop. It waited out the
        whole timeout while the program was on screen.
        """
        text = (REPO / "packaging" / "start.cmd").read_text(encoding="utf-8")
        command = next(line for line in text.splitlines()
                       if line.startswith("powershell "))
        assert "MainWindowHandle" in command
        assert "WaitForInputIdle" not in command, (
            "the launcher still waits on the process it started"
        )

    def test_the_batch_launcher_notices_the_program_stopping(self):
        """Otherwise a program that dies on startup leaves the console sitting
        there for the whole timeout saying it is still waiting.
        """
        text = (REPO / "packaging" / "start.cmd").read_text(encoding="utf-8")
        assert "HasExited" in text

    def test_the_batch_launcher_wait_can_be_bounded_for_a_test(self):
        """The release runs this path with a short timeout. Without the knob
        it would either hang a job for three minutes or not be run at all,
        and not being run at all is how the onefile bug shipped.
        """
        text = (REPO / "packaging" / "start.cmd").read_text(encoding="utf-8")
        assert "_LAUNCH_TIMEOUT" in text

    def test_the_batch_launcher_starts_the_program_exactly_once(self):
        """The failure to avoid: PowerShell starts the program, then reports
        something the batch file reads as "it did not start", and the fallback
        starts a second copy. Every path that can start it has to be reachable
        only before PowerShell has run.
        """
        text = (REPO / "packaging" / "start.cmd").read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines()]

        starts = [i for i, line in enumerate(lines) if line == 'start "" "%EXE%"']
        assert len(starts) == 1, "more than one place starts the program"

        powershell = next(i for i, line in enumerate(lines) if line.startswith("powershell "))
        jumps = [i for i, line in enumerate(lines) if "goto :handoff" in line]
        assert jumps, "nothing checks for PowerShell before relying on it"
        assert all(i < powershell for i in jumps), (
            "a jump to the fallback after PowerShell would start a second copy"
        )

        # cmd.exe runs straight through a label. The line above :handoff has to
        # stop, or every path that already started the program falls into it.
        label = lines.index(":handoff")
        previous = next(
            lines[i] for i in range(label - 1, -1, -1) if lines[i] and not lines[i].startswith("rem")
        )
        assert previous.startswith("exit /b"), (
            f"execution falls through into :handoff from {previous!r}"
        )

    def test_the_launcher_does_not_claim_to_prove_authorship(self):
        """The digest ships in the same archive as the file it describes. It
        catches damage, not tampering, and saying otherwise would be worse
        than saying nothing.
        """
        for name in ("start.sh", "start.cmd"):
            text = (REPO / "packaging" / name).read_text(encoding="utf-8").lower()
            assert "tampering" in text, f"packaging/{name} does not say what it cannot do"


def test_the_windows_archive_unpacks_to_the_same_folder_as_the_others():
    """7z stores the path it is given, not just the leaf.

    Called on `dist/pkg/P7M Manager` it produces an archive that unpacks to
    `dist/pkg/P7M Manager/`, three levels deeper than the Linux tarball. A
    release shipped that way once, in one of these products. Running it from
    inside the payload's parent, with the bare folder name, is what makes all
    three unpack the same way.
    """
    run = step_named(build_steps(load_workflow()), "Package")["run"]
    assert 'parent="$(dirname "$PAYLOAD")"' in run, (
        "7z is not run from the payload's parent"
    )
    assert 'folder="$(basename "$PAYLOAD")"' in run, (
        "7z is given a path rather than a bare folder name"
    )
    assert 'cd "$parent" && 7z a -tzip "$out/$archive" "$folder"' in run


def test_the_release_stops_if_the_tag_and_the_program_disagree():
    """The tag names the archive; the program has a version of its own, and
    nothing used to make the two agree. A `v1.0.0` tag would produce an
    archive called 1.0.0 holding a program that answers `--version` with
    something else — a download whose name contradicts its contents, which is
    the one thing a release must not be.
    """
    step = step_named(build_steps(load_workflow()), "Smoke-test the bundle")
    assert "needs.release.outputs.version" in step["env"].get("VERSION", ""), (
        "the smoke test cannot see the version the tag asked for"
    )
    assert "the tag says" in step["run"], "nothing compares the tag to the program"


def test_the_version_comparison_survives_a_windows_line_ending():
    """A Windows build prints CRLF. Comparing without stripping the carriage
    return fails on every Windows release and passes everywhere else, which is
    the worst way for a check like this to be wrong.
    """
    step = step_named(build_steps(load_workflow()), "Smoke-test the bundle")
    assert "--version | tr -d" in step["run"], (
        "the version is compared without stripping the carriage return"
    )
