#!/usr/bin/env python3

import argparse
import configparser
from pathlib import Path


def load_config(path: Path) -> configparser.RawConfigParser:
    config = configparser.RawConfigParser()

    if path.is_file():
        config.read(path, encoding="utf-8")

    return config


def resolve_profile(root: Path) -> tuple[Path, str]:
    root = root.expanduser().resolve()
    profiles_ini = root / "profiles.ini"
    installs_ini = root / "installs.ini"

    if not profiles_ini.is_file():
        raise SystemExit(
            f"Firefox profiles.ini is missing: {profiles_ini}"
        )

    profiles_config = load_config(profiles_ini)
    profiles: list[dict[str, object]] = []

    for section in profiles_config.sections():
        if not section.startswith("Profile"):
            continue

        raw_path = profiles_config.get(
            section,
            "Path",
            fallback="",
        )

        if not raw_path:
            continue

        is_relative = profiles_config.getboolean(
            section,
            "IsRelative",
            fallback=True,
        )

        path = (
            root / raw_path
            if is_relative
            else Path(raw_path)
        ).expanduser().resolve()

        profiles.append({
            "section": section,
            "name": profiles_config.get(
                section,
                "Name",
                fallback="",
            ),
            "default": profiles_config.getboolean(
                section,
                "Default",
                fallback=False,
            ),
            "path": path,
        })

    if not profiles:
        raise SystemExit(
            "No Firefox profiles are declared."
        )

    installation_candidates: list[
        tuple[Path, bool, str]
    ] = []

    def collect_install_mappings(
        config: configparser.RawConfigParser,
        source_name: str,
    ) -> None:
        for section in config.sections():
            if (
                source_name == "profiles.ini"
                and not section.startswith("Install")
            ):
                continue

            default_value = config.get(
                section,
                "Default",
                fallback="",
            )

            if not default_value:
                continue

            path = (
                root / default_value
            ).expanduser().resolve()

            locked = config.getboolean(
                section,
                "Locked",
                fallback=False,
            )

            if path.is_dir():
                installation_candidates.append(
                    (
                        path,
                        locked,
                        f"{source_name}:{section}",
                    )
                )

    collect_install_mappings(
        profiles_config,
        "profiles.ini",
    )

    installs_config = load_config(installs_ini)

    collect_install_mappings(
        installs_config,
        "installs.ini",
    )

    def unique_paths(
        candidates: list[tuple[Path, bool, str]],
    ) -> list[Path]:
        result: list[Path] = []

        for path, _locked, _source in candidates:
            if path not in result:
                result.append(path)

        return result

    locked_paths = unique_paths([
        candidate
        for candidate in installation_candidates
        if candidate[1]
    ])

    if len(locked_paths) == 1:
        return (
            locked_paths[0],
            "locked-installation-default",
        )

    if len(locked_paths) > 1:
        raise SystemExit(
            "Multiple locked Firefox installation "
            f"defaults were found: {locked_paths}"
        )

    installation_paths = unique_paths(
        installation_candidates
    )

    if len(installation_paths) == 1:
        return (
            installation_paths[0],
            "installation-default",
        )

    if len(installation_paths) > 1:
        raise SystemExit(
            "Multiple Firefox installation defaults "
            f"were found: {installation_paths}"
        )

    default_profiles = [
        profile["path"]
        for profile in profiles
        if profile["default"]
        and Path(profile["path"]).is_dir()
    ]

    if len(default_profiles) == 1:
        return (
            Path(default_profiles[0]),
            "profiles-ini-default-fallback",
        )

    release_profiles = [
        Path(profile["path"])
        for profile in profiles
        if (
            Path(profile["path"]).is_dir()
            and (
                profile["name"] == "default-release"
                or Path(profile["path"]).name.endswith(
                    ".default-release"
                )
            )
        )
    ]

    if len(release_profiles) == 1:
        return (
            release_profiles[0],
            "default-release-fallback",
        )

    usable_profiles = [
        Path(profile["path"])
        for profile in profiles
        if (
            Path(profile["path"]).is_dir()
            and (
                Path(profile["path"]) / "prefs.js"
            ).is_file()
        )
    ]

    if len(usable_profiles) == 1:
        return (
            usable_profiles[0],
            "single-used-profile-fallback",
        )

    raise SystemExit(
        "Firefox profile selection is ambiguous."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve the profile belonging to the "
            "current Firefox installation."
        )
    )

    parser.add_argument(
        "firefox_root",
        type=Path,
    )

    output_group = parser.add_mutually_exclusive_group()

    output_group.add_argument(
        "--explain",
        action="store_true",
    )

    output_group.add_argument(
        "--method",
        action="store_true",
        help="Print only the profile resolution method.",
    )

    arguments = parser.parse_args()

    profile, method = resolve_profile(
        arguments.firefox_root
    )

    if not profile.is_dir():
        raise SystemExit(
            f"Resolved profile does not exist: {profile}"
        )

    if arguments.explain:
        print(f"Profile: {profile}")
        print(f"Resolution: {method}")
    elif arguments.method:
        print(method)
    else:
        print(profile)


if __name__ == "__main__":
    main()
