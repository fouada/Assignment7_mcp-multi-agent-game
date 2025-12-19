"""Game layer implementation."""

from .odd_even import OddEvenGame, OddEvenRules, Move, RoundResult, GameResult, GameRole
from .match import Match, MatchState
from .registry import (
    GameRegistry,
    GameInterface,
    GameTypeInfo,
    GameMove,
    GameRoundResult,
    register_default_games,
)

__all__ = [
    # Odd/Even game
    "OddEvenGame",
    "OddEvenRules",
    "Move",
    "RoundResult",
    "GameResult",
    "GameRole",
    # Match management
    "Match",
    "MatchState",
    # Game Registry
    "GameRegistry",
    "GameInterface",
    "GameTypeInfo",
    "GameMove",
    "GameRoundResult",
    "register_default_games",
]

