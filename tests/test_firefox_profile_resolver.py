import importlib.util
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
RESOLVER_PATH = (
    REPOSITORY
    / "scripts"
    / "mobile"
    / "resolve-firefox-profile.py"
)

SPEC = importlib.util.spec_from_file_location(
    "helm_firefox_profile_resolver",
    RESOLVER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Unable to load Firefox profile resolver."
    )

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FirefoxProfileResolverTests(unittest.TestCase):
    def create_profile(
        self,
        root: Path,
        name: str,
        *,
        prefs: bool = False,
    ) -> Path:
        profile = root / name
        profile.mkdir(parents=True)

        if prefs:
            (profile / "prefs.js").write_text(
                "// test profile\n",
                encoding="utf-8",
            )

        return profile

    def write_profiles(
        self,
        root: Path,
        text: str,
    ) -> None:
        (root / "profiles.ini").write_text(
            text.strip() + "\n",
            encoding="utf-8",
        )

    def test_locked_installation_default_beats_default_flag(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            fallback = self.create_profile(
                root,
                "unused.default",
            )

            release = self.create_profile(
                root,
                "active.default-release",
                prefs=True,
            )

            self.write_profiles(
                root,
                """
[Profile1]
Name=default
IsRelative=1
Path=unused.default
Default=1

[Profile0]
Name=default-release
IsRelative=1
Path=active.default-release
""",
            )

            (root / "installs.ini").write_text(
                """
[TESTINSTALL]
Default=active.default-release
Locked=1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            profile, method = MODULE.resolve_profile(
                root
            )

            self.assertEqual(profile, release.resolve())
            self.assertNotEqual(profile, fallback.resolve())
            self.assertEqual(
                method,
                "locked-installation-default",
            )

    def test_profiles_ini_install_mapping_is_supported(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            release = self.create_profile(
                root,
                "release.default-release",
            )

            self.write_profiles(
                root,
                """
[InstallABCDEF]
Default=release.default-release
Locked=1

[Profile0]
Name=default-release
IsRelative=1
Path=release.default-release
""",
            )

            profile, method = MODULE.resolve_profile(
                root
            )

            self.assertEqual(profile, release.resolve())
            self.assertEqual(
                method,
                "locked-installation-default",
            )

    def test_default_flag_is_used_only_as_fallback(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            default = self.create_profile(
                root,
                "fallback.default",
            )

            self.create_profile(
                root,
                "other.profile",
            )

            self.write_profiles(
                root,
                """
[Profile1]
Name=default
IsRelative=1
Path=fallback.default
Default=1

[Profile0]
Name=other
IsRelative=1
Path=other.profile
""",
            )

            profile, method = MODULE.resolve_profile(
                root
            )

            self.assertEqual(profile, default.resolve())
            self.assertEqual(
                method,
                "profiles-ini-default-fallback",
            )

    def test_multiple_locked_defaults_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            self.create_profile(root, "first.default")
            self.create_profile(root, "second.default")

            self.write_profiles(
                root,
                """
[Profile0]
Name=first
IsRelative=1
Path=first.default

[Profile1]
Name=second
IsRelative=1
Path=second.default
""",
            )

            (root / "installs.ini").write_text(
                """
[FIRST]
Default=first.default
Locked=1

[SECOND]
Default=second.default
Locked=1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                MODULE.resolve_profile(root)


if __name__ == "__main__":
    unittest.main()
