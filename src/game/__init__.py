"""Game layer implementation."""

from .match import Match, MatchState
from .odd_even import GameResult, GameRole, Move, OddEvenGame, OddEvenRules, RoundResult
from .registry import (
    GameInterface,
    GameMove,
    GameRegistry,
    GameRoundResult,
    GameTypeInfo,
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
