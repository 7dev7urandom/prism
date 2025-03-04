import functools
import logging
import queue
from typing import Iterable

from examples.overlay.controller import OverlayController
from examples.overlay.get_stats import get_bedwars_stats
from examples.overlay.parsing import parse_logline
from examples.overlay.player import MISSING_WINSTREAKS, KnownPlayer
from examples.overlay.process_event import process_event
from examples.overlay.settings import SettingsDict

logger = logging.getLogger(__name__)


def set_nickname(
    *, username: str | None, nick: str, controller: OverlayController
) -> None:
    """Update the user's nickname"""
    logger.debug(f"Setting denick {nick=} => {username=}")

    old_nick = None

    if username is not None:
        uuid = controller.get_uuid(username)

        if uuid is None:
            logger.error(f"Failed getting uuid for '{username}' when setting nickname.")
            # Delete the entry for this nick
            old_nick = nick
    else:
        uuid = None
        # Delete the entry for this nick
        old_nick = nick

    with controller.settings.mutex:
        if uuid is not None and username is not None:
            # Search the known nicks in settings for the uuid
            for old_nick, nick_value in controller.settings.known_nicks.items():
                if uuid == nick_value["uuid"]:
                    new_nick_value = nick_value
                    break
            else:
                # Found no matching entries - make a new one
                new_nick_value = {"uuid": uuid, "comment": username}
                old_nick = None
        else:
            new_nick_value = None

        # Remove the old nick if found
        if old_nick is not None:
            controller.settings.known_nicks.pop(old_nick, None)

        if new_nick_value is not None:
            # Add your new nick
            controller.settings.known_nicks[nick] = new_nick_value

        controller.store_settings()

    with controller.nick_database.mutex:
        # Delete your old nick if found
        if old_nick is not None:
            controller.nick_database.default_database.pop(old_nick, None)

        if uuid is not None:
            # Add your new nick
            controller.nick_database.default_database[nick] = uuid

    if old_nick is not None:
        # Drop the stats cache for your old nick
        controller.player_cache.uncache_player(old_nick)

    # Drop the stats cache for your new nick so that we can fetch the stats
    controller.player_cache.uncache_player(nick)

    controller.redraw_event.set()


def set_hypixel_api_key(new_key: str, /, controller: OverlayController) -> None:
    """Update the API key that the download threads use"""
    controller.set_hypixel_api_key(new_key)
    controller.api_key_invalid = False

    with controller.settings.mutex:
        controller.settings.hypixel_api_key = new_key
        controller.store_settings()

    # Clear the stats cache in case the old api key was invalid
    controller.player_cache.clear_cache()


def fast_forward_state(controller: OverlayController, loglines: Iterable[str]) -> None:
    """Process the state changes for each logline without outputting anything"""
    logger.info("Fast forwarding state")
    for line in loglines:
        event = parse_logline(line)

        if event is None:
            continue

        process_event(controller, event)
    logger.info("Done fast forwarding state")


def process_loglines(loglines: Iterable[str], controller: OverlayController) -> None:
    """Update state and set the redraw event"""
    for line in loglines:
        event = parse_logline(line)

        if event is None:
            continue

        with controller.state.mutex:
            redraw = process_event(controller, event)

        if redraw:
            # Tell the main thread we need a redraw
            controller.redraw_event.set()


def should_redraw(
    controller: OverlayController, completed_stats_queue: queue.Queue[str]
) -> bool:
    """Check if any updates happened since last time that needs a redraw"""
    # Check if the state update thread has issued any redraws since last time
    redraw = controller.redraw_event.is_set()

    # Check if any of the stats downloaded since last render are still in the lobby
    while True:
        try:
            username = completed_stats_queue.get_nowait()
        except queue.Empty:
            break
        else:
            completed_stats_queue.task_done()
            if not redraw:
                with controller.state.mutex:
                    if username in controller.state.lobby_players:
                        # We just received the stats of a player in the lobby
                        # Redraw the screen in case the stats weren't there last time
                        redraw = True

    if redraw:
        # We are going to redraw - clear any redraw request
        controller.redraw_event.clear()

    return redraw


def get_stats_and_winstreak(
    username: str, completed_queue: queue.Queue[str], controller: OverlayController
) -> None:
    """Get a username from the requests queue and cache their stats"""
    # get_bedwars_stats sets the stats cache which will be read from later
    player = get_bedwars_stats(username, controller)

    # Tell the main thread that we downloaded this user's stats
    completed_queue.put(username)

    logger.debug(f"Finished gettings stats for {username}")

    if isinstance(player, KnownPlayer) and player.is_missing_winstreaks:
        (
            estimated_winstreaks,
            winstreaks_accurate,
        ) = controller.get_estimated_winstreaks(player.uuid)

        if estimated_winstreaks is MISSING_WINSTREAKS:
            logger.debug(f"Updating missing winstreak for {username} failed")
        else:
            for alias in player.aliases:
                controller.player_cache.update_cached_player(
                    alias,
                    functools.partial(
                        KnownPlayer.update_winstreaks,
                        **estimated_winstreaks,
                        winstreaks_accurate=winstreaks_accurate,
                    ),
                )

            # Tell the main thread that we got the estimated winstreak
            completed_queue.put(username)
            logger.debug(f"Updated missing winstreak for {username}")


def update_settings(new_settings: SettingsDict, controller: OverlayController) -> None:
    """
    Update the settings from the settings dict, with required side-effects

    Caller must acquire lock on settings
    """
    logger.debug(f"Updating settings with {new_settings}")

    hypixel_api_key_changed = (
        new_settings["hypixel_api_key"] != controller.settings.hypixel_api_key
    )

    antisniper_api_key_changed = (
        new_settings["antisniper_api_key"] != controller.settings.antisniper_api_key
    )

    use_antisniper_api_changed = (
        new_settings["use_antisniper_api"] != controller.settings.use_antisniper_api
    )

    # True if the stats could be affected by the settings update
    potential_antisniper_updates = (
        # Changing their key and intending to use the api
        antisniper_api_key_changed
        and new_settings["use_antisniper_api"]
    ) or (
        # Turning the api on/off with an active key
        use_antisniper_api_changed
        and new_settings["antisniper_api_key"] is not None
    )

    # Known_nicks
    def uuid_changed(nickname: str) -> bool:
        """True if the uuid of the given nickname changed in new_settings"""
        return (
            new_settings["known_nicks"][nickname]
            != controller.settings.known_nicks[nickname]
        )

    new_nicknames = set(new_settings["known_nicks"].keys())
    old_nicknames = set(controller.settings.known_nicks.keys())

    added_nicknames = new_nicknames - old_nicknames
    removed_nicknames = old_nicknames - new_nicknames
    updated_nicknames = set(
        filter(uuid_changed, set.intersection(new_nicknames, old_nicknames))
    )

    # Update the player cache
    if hypixel_api_key_changed or potential_antisniper_updates:
        logger.debug("Clearing whole player cache due to api key changes")
        controller.player_cache.clear_cache()
    else:
        # Refetch stats for nicknames that had a player assigned or unassigned
        # for nickname in added_nicknames + removed_nicknames:
        for nickname in set.union(added_nicknames, removed_nicknames):
            controller.player_cache.uncache_player(nickname)

        # Refetch stats for nicknames that were assigned to a different player
        for nickname in updated_nicknames:
            controller.player_cache.uncache_player(nickname)

    # Update default nick database
    # NOTE: Since the caller must acquire the settings lock, we have two locks here
    # Make sure that we always acquire the settings lock before the nick database lock
    # to avoid deadlocks
    with controller.nick_database.mutex:
        for nickname in removed_nicknames:
            controller.nick_database.default_database.pop(nickname, None)

        for nickname in set.union(added_nicknames, updated_nicknames):
            controller.nick_database.default_database[nickname] = new_settings[
                "known_nicks"
            ][nickname]["uuid"]

    # Redraw the overlay to reflect changes in the stats cache/nicknames
    controller.redraw_event.set()

    controller.settings.update_from(new_settings)

    controller.store_settings()
