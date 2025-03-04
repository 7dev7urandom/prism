import dataclasses
from pathlib import Path
from typing import Any

import pytest

from examples.overlay.settings import (
    PLACEHOLDER_API_KEY,
    NickValue,
    Settings,
    SettingsDict,
    ValueType,
    fill_missing_settings,
    get_settings,
    read_settings,
    value_or_default,
)
from tests.examples.overlay.utils import make_settings

KEY_IF_MISSING = "KEY_IF_MISSING"


def make_settings_dict(
    hypixel_api_key: str | None = None,
    antisniper_api_key: str | None = None,
    use_antisniper_api: bool | None = None,
    known_nicks: dict[str, NickValue] | None = None,
    show_on_tab: bool | None = None
) -> SettingsDict:
    """Make a settings dict with default values if missing"""
    return {
        "hypixel_api_key": hypixel_api_key or KEY_IF_MISSING,
        "antisniper_api_key": antisniper_api_key or PLACEHOLDER_API_KEY,
        "use_antisniper_api": use_antisniper_api or False,
        "known_nicks": known_nicks or {},
        "show_on_tab": show_on_tab or True
    }


def get_api_key() -> str:
    return KEY_IF_MISSING


PLACEHOLDER_PATH = Path("PLACEHOLDER_PATH")

settings_to_dict_cases: tuple[tuple[Settings, SettingsDict], ...] = (
    (
        Settings(
            hypixel_api_key="my-key",
            antisniper_api_key="my-key",
            use_antisniper_api=True,
            known_nicks={"AmazingNick": {"uuid": "123987", "comment": "Player1"}},
            path=PLACEHOLDER_PATH,
            show_on_tab=True
        ),
        {
            "hypixel_api_key": "my-key",
            "antisniper_api_key": "my-key",
            "use_antisniper_api": True,
            "known_nicks": {"AmazingNick": {"uuid": "123987", "comment": "Player1"}},
            "show_on_tab": True
        },
    ),
)


@pytest.mark.parametrize("settings, result", settings_to_dict_cases)
def test_settings_to_dict(settings: Settings, result: SettingsDict) -> None:
    assert settings.to_dict() == result


@pytest.mark.parametrize(
    "settings_dict, result", tuple((t[1], t[0]) for t in settings_to_dict_cases)
)
def test_settings_from_dict(settings_dict: SettingsDict, result: Settings) -> None:
    assert Settings.from_dict(settings_dict, path=PLACEHOLDER_PATH) == result


@pytest.mark.parametrize(
    "settings_dict, result", tuple((t[1], t[0]) for t in settings_to_dict_cases)
)
def test_settings_update_from(settings_dict: SettingsDict, result: Settings) -> None:
    settings = Settings.from_dict(make_settings_dict(), path=PLACEHOLDER_PATH)
    settings.update_from(settings_dict)
    assert settings == result


@pytest.mark.parametrize(
    "value, default, result",
    (
        (None, 1, 1),
        (2, 1, 2),
        (None, 1.0, 1.0),
        ("str", 1.0, "str"),
        (None, "default", "default"),
        ("test", "default", "test"),
        (None, None, None),
        ("str", None, "str"),
    ),
)
def test_value_or_default(
    value: ValueType | None, default: ValueType, result: ValueType
) -> None:
    assert value_or_default(value, default=default) == result


@pytest.mark.parametrize("settings, settings_dict", settings_to_dict_cases)
def test_read_and_write_settings(
    settings: Settings, settings_dict: SettingsDict, tmp_path: Path
) -> None:
    # Make a copy so we can mutate it
    settings = dataclasses.replace(settings)

    settings.path = tmp_path / "settings.toml"
    settings.flush_to_disk()

    read_settings_dict = read_settings(settings.path)

    assert read_settings_dict == settings_dict

    assert get_settings(settings.path, get_api_key) == settings

    # Assert that get_settings doesn't fail when file doesn't exist
    empty_path = tmp_path / "settings2.toml"
    assert get_settings(empty_path, get_api_key) == Settings(
        path=empty_path, **make_settings_dict()
    )


def test_flush_settings_from_controller(tmp_path: Path) -> None:
    from examples.overlay.controller import RealOverlayController
    from examples.overlay.nick_database import NickDatabase
    from tests.examples.overlay.utils import create_state

    settings = make_settings(hypixel_api_key="my-key", path=tmp_path / "settings.toml")

    # File not found
    assert get_settings(settings.path, get_api_key) != settings

    controller = RealOverlayController(
        state=create_state(), settings=settings, nick_database=NickDatabase([{}])
    )

    controller.store_settings()

    # File properly stored
    assert get_settings(settings.path, get_api_key) == settings


fill_settings_test_cases: tuple[tuple[dict[str, Any], SettingsDict, bool], ...] = (
    (
        {
            "hypixel_api_key": "my-key",
            "antisniper_api_key": "my-key",
            "use_antisniper_api": False,
            "known_nicks": {"AmazingNick": {"uuid": "123987", "comment": "Player1"}},
            "show_on_tab": True
        },
        make_settings_dict(
            hypixel_api_key="my-key",
            antisniper_api_key="my-key",
            known_nicks={"AmazingNick": {"uuid": "123987", "comment": "Player1"}},
            show_on_tab=True,
        ),
        False,
    ),
    (
        {"hypixel_api_key": "my-key"},
        make_settings_dict(hypixel_api_key="my-key"),
        True,
    ),
    (
        {"hypixel_api_key": 1},
        make_settings_dict(),
        True,
    ),
    (
        {"hypixel_api_key": None},
        make_settings_dict(),
        True,
    ),
    (
        {
            "hypixel_api_key": {},
            "known_nicks": {"AmazingNick": {"uuid": "123987", "comment": "Player1"}},
        },
        make_settings_dict(
            known_nicks={"AmazingNick": {"uuid": "123987", "comment": "Player1"}}
        ),
        True,
    ),
    (
        {"antisniper_api_key": None},
        make_settings_dict(),
        True,
    ),
    (
        {"hypixel_api_key": "my-key", "use_antisniper_api": True},
        make_settings_dict(hypixel_api_key="my-key", use_antisniper_api=True),
        True,
    ),
    # Placeholder key
    (
        {"hypixel_api_key": PLACEHOLDER_API_KEY},
        make_settings_dict(),
        True,
    ),
    # Key too short
    (
        {"hypixel_api_key": "k"},
        make_settings_dict(),
        True,
    ),
    (
        {"antisniper_api_key": "k"},
        make_settings_dict(),
        True,
    ),
    # No settings
    ({}, make_settings_dict(), True),
    # Corrupt data in known_nicks
    (
        {
            "hypixel_api_key": "my-key",
            "known_nicks": {
                # Key is not a string
                1234: {"uuid": 123987, "comment": "Player1"}
            },
        },
        make_settings_dict(hypixel_api_key="my-key"),
        True,
    ),
    (
        {
            "hypixel_api_key": "my-key",
            "known_nicks": {
                # Value is a string, not a dict
                "AmazingNick": "uuid"
                "123987"
                "comment"
                "Player1"
            },
        },
        make_settings_dict(hypixel_api_key="my-key"),
        True,
    ),
    (
        {
            "hypixel_api_key": "my-key",
            "known_nicks": {
                # Incorrect type on uuid or comment
                "AmazingNick": {"uuid": 123987, "comment": "Player1"}
            },
        },
        make_settings_dict(hypixel_api_key="my-key"),
        True,
    ),
    (
        {
            "hypixel_api_key": "my-key",
            "known_nicks": {
                # Incorrect type on uuid or comment
                "AmazingNick": {"uuid": "123987", "comment": 1234}
            },
        },
        make_settings_dict(hypixel_api_key="my-key"),
        True,
    ),
)


@pytest.mark.parametrize(
    "incomplete_settings, result_dict, result_updated", fill_settings_test_cases
)
def test_fill_missing_settings(
    incomplete_settings: dict[str, Any], result_dict: SettingsDict, result_updated: bool
) -> None:
    settings_dict, settings_updated = fill_missing_settings(
        incomplete_settings, get_api_key
    )
    assert settings_dict == result_dict
    assert settings_updated == result_updated
