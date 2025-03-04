import logging
from dataclasses import replace

from examples.overlay.controller import OverlayController
from examples.overlay.player import (
    KnownPlayer,
    NickedPlayer,
    PendingPlayer,
    create_known_player,
)

logger = logging.getLogger(__name__)


def denick(nick: str, controller: OverlayController) -> str | None:
    """Try denicking via the antisniper API, fallback to dict"""
    uuid = controller.nick_database.get_default(nick)

    # Return if the user has specified a denick
    if uuid is not None:
        logger.debug(f"Denicked with default database {nick} -> {uuid}")
        return uuid

    uuid = controller.denick(nick)

    if uuid is not None:
        logger.debug(f"Denicked with api {nick} -> {uuid}")
        return uuid

    uuid = controller.nick_database.get(nick)

    if uuid is not None:
        logger.debug(f"Denicked with database {nick} -> {uuid}")
        return uuid

    logger.debug(f"Failed denicking {nick}")

    return None


def fetch_bedwars_stats(
    username: str, controller: OverlayController
) -> KnownPlayer | NickedPlayer:
    """Fetches the bedwars stats for the given player"""
    uuid = controller.get_uuid(username)

    # Look up in nick database if we got no match from Mojang
    nick: str | None = None
    denicked = False
    if uuid is None:
        denick_result = denick(username, controller)
        if denick_result is not None:
            uuid = denick_result
            nick = username
            denicked = True
            logger.debug(f"De-nicked {username} as {uuid}")

    if uuid is None:
        # Could not find uuid or denick - assume nicked
        return NickedPlayer(nick=username)

    playerdata = controller.get_player_data(uuid)

    logger.debug(
        f"Initial stats for {username} ({uuid}) {denicked=} {playerdata is None=}"
    )

    if not denicked and playerdata is None:
        # The username may be an existing minecraft account that has not
        # logged on to Hypixel. Then we would get a hit from Mojang, but
        # no hit from Hypixel and the username is still a nickname.
        denick_result = denick(username, controller)
        if denick_result is not None:
            uuid = denick_result
            nick = username
            logger.debug(f"De-nicked {username} as {uuid} after hit from Mojang")
            playerdata = controller.get_player_data(uuid)
            logger.debug(f"Stats for nicked {nick} ({uuid}) {playerdata is None=}")

    if playerdata is None:
        logger.debug("Got no playerdata - assuming player is nicked")
        return NickedPlayer(nick=username)

    if nick is not None:
        # Successfully de-nicked - update actual username
        username = playerdata["displayname"]
        logger.debug(f"De-nicked {nick} as {username}")

    return create_known_player(playerdata, username=username, uuid=uuid, nick=nick)


def get_bedwars_stats(
    username: str,
    controller: OverlayController,
) -> KnownPlayer | NickedPlayer:
    """Get and caches the bedwars stats for the given player"""
    cached_stats = controller.player_cache.get_cached_player(username)

    if cached_stats is not None and not isinstance(cached_stats, PendingPlayer):
        logger.debug(f"Cache hit {username}")

        return cached_stats

    logger.debug(f"Cache miss {username}")

    player = fetch_bedwars_stats(username, controller)

    if isinstance(player, KnownPlayer) and player.nick is not None:
        # If we look up by actual username, that means the user is not nicked
        controller.player_cache.set_cached_player(
            player.username, replace(player, nick=None)
        )

    controller.player_cache.set_cached_player(username, player)

    return player
