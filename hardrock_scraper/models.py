"""Data models for HardRock table tennis scraper"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MatchStatus(Enum):
    LIVE = "live"
    UPCOMING = "upcoming"
    ENDED = "ended"


@dataclass
class Player:
    """Represents a table tennis player"""
    name: str
    ranking: Optional[int] = None
    country: Optional[str] = None
    
    def __str__(self) -> str:
        return self.name


@dataclass
class Score:
    """Represents match score information"""
    current_set: int
    set_scores: List[str]  # ["6-4", "3-6", "2-1"] format
    total_games: Optional[str] = None  # Overall games if available
    
    def __str__(self) -> str:
        return f"Set {self.current_set}: {' | '.join(self.set_scores)}"


@dataclass
class Odds:
    """Represents betting odds for a match"""
    player1_moneyline: Optional[str] = None
    player2_moneyline: Optional[str] = None
    handicap_line: Optional[str] = None
    player1_handicap: Optional[str] = None
    player2_handicap: Optional[str] = None
    over_under_line: Optional[str] = None
    over_odds: Optional[str] = None
    under_odds: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Match:
    """Represents a table tennis match"""
    match_id: str
    player1: Player
    player2: Player
    status: MatchStatus
    score: Optional[Score] = None
    odds: Optional[Odds] = None
    start_time: Optional[datetime] = None
    league: Optional[str] = None
    tournament: Optional[str] = None
    
    def is_live(self) -> bool:
        return self.status == MatchStatus.LIVE
    
    def is_upcoming(self) -> bool:
        return self.status == MatchStatus.UPCOMING
    
    def __str__(self) -> str:
        status_str = self.status.value.upper()
        score_str = f" ({self.score})" if self.score else ""
        return f"{status_str}: {self.player1.name} vs {self.player2.name}{score_str}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert match to dictionary for easy serialization"""
        return {
            "match_id": self.match_id,
            "player1": {
                "name": self.player1.name,
                "ranking": self.player1.ranking,
                "country": self.player1.country
            },
            "player2": {
                "name": self.player2.name,
                "ranking": self.player2.ranking,
                "country": self.player2.country
            },
            "status": self.status.value,
            "score": {
                "current_set": self.score.current_set,
                "set_scores": self.score.set_scores,
                "total_games": self.score.total_games
            } if self.score else None,
            "odds": {
                "player1_moneyline": self.odds.player1_moneyline,
                "player2_moneyline": self.odds.player2_moneyline,
                "handicap_line": self.odds.handicap_line,
                "player1_handicap": self.odds.player1_handicap,
                "player2_handicap": self.odds.player2_handicap,
                "over_under_line": self.odds.over_under_line,
                "over_odds": self.odds.over_odds,
                "under_odds": self.odds.under_odds,
                "timestamp": self.odds.timestamp.isoformat() if self.odds.timestamp else None
            } if self.odds else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "league": self.league,
            "tournament": self.tournament
        }