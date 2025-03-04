import threading
import unittest.mock
from pathlib import Path
from typing import Sequence, cast

from examples.overlay.user_interaction import (
    file_exists,
    get_timestamp,
    search_logfile_for_key,
    search_settings_file_for_key,
    suggest_logfiles,
)
from tests.mock_utils import Line, MockedIOModule, MockedOsModule, create_mocked_file

UNSET_EVENT = threading.Event()
SET_EVENT = threading.Event()
SET_EVENT.set()

INFO = "[Client thread/INFO]: "
CHAT = "[Client thread/INFO]: [CHAT] "


def test_file_exists_no() -> None:
    assert not file_exists("ThisPathDoesNotExists")
    assert not file_exists(Path("ThisPathDoesNotExists"))


def test_file_exists_yes(tmp_path: Path) -> None:
    # A directory is not a file
    assert not file_exists(str(tmp_path))
    assert not file_exists(tmp_path)
    file_path = tmp_path / "newfile"

    with file_path.open("w") as f:
        f.write("hi")

    assert file_exists(str(file_path))
    assert file_exists(file_path)


def test_suggest_logfiles() -> None:
    suggestions = suggest_logfiles()
    assert all(map(file_exists, suggestions))


def test_get_timestamp(tmp_path: Path) -> None:
    file_path = tmp_path / "newfile"

    with file_path.open("w") as f:
        f.write("hi")

    assert get_timestamp(str(file_path)) == file_path.stat().st_mtime

    assert get_timestamp(str(tmp_path / "doesnotexist")) == 0


@unittest.mock.patch("toml.decoder.io", MockedIOModule)
@unittest.mock.patch("os.fspath", MockedOsModule.fspath)
def test_search_settings_file_for_key() -> None:
    mocked_path, mocked_file, mocked_time = create_mocked_file(
        (
            Line(0, 'hypixel_api_key = "insert-your-key-here"'),
            Line(2, None),
            Line(2, 'hypixel_api_key = "new'),  # invalid syntax
            Line(3, None),
            Line(10, 'hypixel_api_key = "new-api-key"'),
        ),
        amt_opens=1000,
    )

    with unittest.mock.patch(
        "examples.overlay.user_interaction.time", mocked_time.time
    ):
        found_key = search_settings_file_for_key(cast(Path, mocked_path), UNSET_EVENT)

    assert found_key == "new-api-key"
    assert mocked_time.current_time == 10
    assert [call[0] for call in mocked_path.calls] == [0, 1, 2, 7, 8, 9, 10]


def test_search_settings_file_for_key_event_set() -> None:
    mocked_path, mocked_file, mocked_time = create_mocked_file((), amt_opens=0)
    with unittest.mock.patch(
        "examples.overlay.user_interaction.time", mocked_time.time
    ):
        found_key = search_settings_file_for_key(cast(Path, mocked_path), SET_EVENT)

    assert found_key is None
    assert mocked_time.current_time == 0
    assert [call[0] for call in mocked_path.calls] == []


def perform_search_logfile_for_key(
    lines: Sequence[Line], event_set: bool = False
) -> tuple[str | None, float]:
    mocked_path, mocked_file, mocked_time = create_mocked_file(lines, amt_opens=1000)

    with (
        unittest.mock.patch("examples.overlay.file_utils.time", mocked_time.time),
        unittest.mock.patch(
            "examples.overlay.file_utils.datetime", mocked_time.datetime
        ),
        unittest.mock.patch("examples.overlay.file_utils.date", mocked_time.date),
    ):
        found_key = search_logfile_for_key(
            cast(Path, mocked_path), SET_EVENT if event_set else UNSET_EVENT
        )

    return found_key, mocked_time.current_time


def test_search_logfile_for_key_single() -> None:
    found_key, current_time = perform_search_logfile_for_key(
        (
            Line(0, f"{INFO}Setting user: Player1"),
            Line(0, f"{CHAT}You are now nicked as AmazingNick"),
            Line(0, f"{CHAT}Your new API key is new-api-key"),
            Line(0, f"{CHAT}You have joined [MVP++] Player2's party!"),
        )
    )

    assert found_key == "new-api-key"
    assert current_time == 0


def test_search_logfile_for_key_multiple() -> None:
    found_key, current_time = perform_search_logfile_for_key(
        (
            Line(0, f"{INFO}Setting user: Player1"),
            Line(0, f"{CHAT}You are now nicked as AmazingNick"),
            Line(0, f"{CHAT}Your new API key is new-api-key"),
            Line(0, f"{CHAT}Your new API key is newer-api-key"),
            Line(0, f"{CHAT}Your new API key is newest-api-key"),
            Line(0, f"{CHAT}You have joined [MVP++] Player2's party!"),
        )
    )

    assert found_key == "newest-api-key"
    assert current_time == 0


def test_search_logfile_for_key_pause() -> None:
    found_key, current_time = perform_search_logfile_for_key(
        (
            Line(0, f"{INFO}Setting user: Player1"),
            Line(0, f"{CHAT}You are now nicked as AmazingNick"),
            Line(1, f"{CHAT}Your new API key is new-api-key"),
            # Later keys should be picked up by the main application
            Line(2, f"{CHAT}Your new API key is even-later-api-key"),
        )
    )

    assert found_key == "new-api-key"
    assert 1 <= current_time <= 2


def test_search_logfile_for_key_event_set() -> None:
    found_key, current_time = perform_search_logfile_for_key(
        (Line(0, f"{CHAT}Your new API key is new-api-key"),),
        event_set=True,
    )

    assert found_key is None
    assert current_time == 0
