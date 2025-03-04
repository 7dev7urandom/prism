from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto, unique
from typing import Literal, Union

logger = logging.getLogger(__name__)


PartyRole = Literal["leader", "moderators", "members"]


@unique
class EventType(Enum):
    # Initialization
    INITIALIZE_AS = auto()  # Initialize as the given username

    # New nickname (/nick reuse)
    NEW_NICKNAME = auto()

    # Lobby join/leave
    LOBBY_SWAP = auto()  # You join a new lobby
    LOBBY_JOIN = auto()  # Someone joins your lobby
    LOBBY_LEAVE = auto()  # Someone leaves your lobby

    # /who
    LOBBY_LIST = auto()  # You get a list of all players in your lobby

    # Party join/leave
    PARTY_ATTACH = auto()  # You join a party
    PARTY_DETACH = auto()  # You leave a party
    PARTY_JOIN = auto()  # Someone joins your party
    PARTY_LEAVE = auto()  # Someone leaves your party

    # /party list (/pl)
    PARTY_LIST_INCOMING = auto()  # The header of the party table
    PARTY_ROLE_LIST = auto()  # List of members or moderators, or the leader

    # Games
    START_BEDWARS_GAME = auto()  # A bedwars game has started
    END_BEDWARS_GAME = auto()  # A bedwars game has ended

    # New API key
    NEW_API_KEY = auto()  # New API key in chat (/api new)

    # Commands /w !<command>
    WHISPER_COMMAND_SET_NICK = auto()


@dataclass
class InitializeAsEvent:
    username: str
    event_type: Literal[EventType.INITIALIZE_AS] = EventType.INITIALIZE_AS


@dataclass
class NewNicknameEvent:
    nick: str
    event_type: Literal[EventType.NEW_NICKNAME] = EventType.NEW_NICKNAME


@dataclass
class LobbySwapEvent:
    event_type: Literal[EventType.LOBBY_SWAP] = EventType.LOBBY_SWAP


@dataclass
class LobbyJoinEvent:
    username: str
    player_count: int
    player_cap: int
    event_type: Literal[EventType.LOBBY_JOIN] = EventType.LOBBY_JOIN


@dataclass
class LobbyLeaveEvent:
    username: str
    event_type: Literal[EventType.LOBBY_LEAVE] = EventType.LOBBY_LEAVE


@dataclass
class LobbyListEvent:
    usernames: list[str]
    event_type: Literal[EventType.LOBBY_LIST] = EventType.LOBBY_LIST


@dataclass
class PartyAttachEvent:
    username: str  # Leader
    event_type: Literal[EventType.PARTY_ATTACH] = EventType.PARTY_ATTACH


@dataclass
class PartyDetachEvent:
    event_type: Literal[EventType.PARTY_DETACH] = EventType.PARTY_DETACH


@dataclass
class PartyJoinEvent:
    usernames: list[str]
    event_type: Literal[EventType.PARTY_JOIN] = EventType.PARTY_JOIN


@dataclass
class PartyLeaveEvent:
    usernames: list[str]
    event_type: Literal[EventType.PARTY_LEAVE] = EventType.PARTY_LEAVE


@dataclass
class PartyListIncomingEvent:
    event_type: Literal[EventType.PARTY_LIST_INCOMING] = EventType.PARTY_LIST_INCOMING


@dataclass
class PartyMembershipListEvent:
    usernames: list[str]
    role: PartyRole  # The users' roles
    event_type: Literal[EventType.PARTY_ROLE_LIST] = EventType.PARTY_ROLE_LIST


@dataclass
class StartBedwarsGameEvent:
    event_type: Literal[EventType.START_BEDWARS_GAME] = EventType.START_BEDWARS_GAME


@dataclass
class EndBedwarsGameEvent:
    event_type: Literal[EventType.END_BEDWARS_GAME] = EventType.END_BEDWARS_GAME


@dataclass
class NewAPIKeyEvent:
    key: str
    event_type: Literal[EventType.NEW_API_KEY] = EventType.NEW_API_KEY


@unique
class WhisperCommandType(Enum):
    SET_NICK = auto()


@dataclass
class WhisperCommandSetNickEvent:
    nick: str
    username: str | None
    event_type: Literal[
        EventType.WHISPER_COMMAND_SET_NICK
    ] = EventType.WHISPER_COMMAND_SET_NICK


ClientEvent = Union[
    InitializeAsEvent,
]

ChatEvent = Union[
    NewNicknameEvent,
    LobbySwapEvent,
    LobbyJoinEvent,
    LobbyLeaveEvent,
    LobbyListEvent,
    PartyAttachEvent,
    PartyDetachEvent,
    PartyJoinEvent,
    PartyLeaveEvent,
    PartyListIncomingEvent,
    PartyMembershipListEvent,
    StartBedwarsGameEvent,
    EndBedwarsGameEvent,
    NewAPIKeyEvent,
    WhisperCommandSetNickEvent,
]

Event = Union[ClientEvent, ChatEvent]
