"""HTML parser for extracting table tennis match data from HardRock sportsbook"""

import re
import logging
from typing import List, Optional, Dict
from datetime import datetime
from bs4 import BeautifulSoup, Tag

from .models import Match, Player, Score, Odds, MatchStatus
from .exceptions import ParseError, DataNotFoundError


class HardRockParser:
    """Parser for HardRock table tennis HTML pages"""
    
    def __init__(self):
        self.soup: Optional[BeautifulSoup] = None
        self.logger = logging.getLogger(__name__)
    
    def parse_html(self, html_content: str) -> List[Match]:
        """Parse HTML content and extract all matches"""
        try:
            self.soup = BeautifulSoup(html_content, 'html.parser')
            matches = []
            
            # Find match containers - these selectors will need adjustment based on actual HTML
            match_containers = self._find_match_containers()
            
            for container in match_containers:
                try:
                    match = self._parse_match_container(container)
                    if match:
                        matches.append(match)
                except Exception as e:
                    # Log error but continue parsing other matches
                    print(f"Error parsing match container: {e}")
                    continue
            
            return matches
            
        except Exception as e:
            raise ParseError(f"Failed to parse HTML content: {e}")
    
    def _find_match_containers(self) -> List[Tag]:
        """Find all match containers in the HTML"""
        # HardRock specific selector
        containers = self.soup.select('.hr-market-view')
        
        if containers:
            self.logger.info(f"Found {len(containers)} match containers using .hr-market-view")
            return containers
        
        # Fallback selectors
        fallback_selectors = [
            '[data-testid*="match"]',
            '[class*="market-view"]',
            '[class*="event"]',
            '.game-card',
            '.match-card'
        ]
        
        for selector in fallback_selectors:
            containers = self.soup.select(selector)
            if containers:
                self.logger.info(f"Found {len(containers)} containers using fallback: {selector}")
                return containers
        
        self.logger.warning("No match containers found")
        return []
    
    def _parse_match_container(self, container: Tag) -> Optional[Match]:
        """Parse a single match container"""
        try:
            # Extract match ID
            match_id = self._extract_match_id(container)
            
            # Extract players
            players = self._extract_players(container)
            if len(players) != 2:
                return None
            
            # Extract match status
            status = self._extract_match_status(container)
            
            # Extract score if live
            score = None
            if status == MatchStatus.LIVE:
                score = self._extract_score(container)
            
            # Extract odds
            odds = self._extract_odds(container)
            
            # Extract additional info
            start_time = self._extract_start_time(container)
            league = self._extract_league(container)
            
            return Match(
                match_id=match_id,
                player1=players[0],
                player2=players[1],
                status=status,
                score=score,
                odds=odds,
                start_time=start_time,
                league=league
            )
            
        except Exception as e:
            raise ParseError(f"Failed to parse match container: {e}")
    
    def _extract_match_id(self, container: Tag) -> str:
        """Extract unique match identifier"""
        # Look for data attributes that might contain match ID
        for attr in ['data-match-id', 'data-event-id', 'data-game-id', 'id']:
            if container.get(attr):
                return str(container[attr])
        
        # Look for HardRock-specific match IDs in wager buttons
        wager_buttons = container.select('[data-tooltip-id]')
        if wager_buttons:
            # Extract the numeric part from data-tooltip-id (e.g., "619477862109151478-619477862109151478")
            tooltip_id = wager_buttons[0].get('data-tooltip-id', '')
            if tooltip_id and '-' in tooltip_id:
                # Use the first part before the dash as match ID
                match_id = tooltip_id.split('-')[0]
                if match_id.isdigit():
                    return match_id
        
        # Fallback: generate ID from player names
        text = container.get_text(strip=True)
        return str(hash(text))[:10]
    
    def _extract_players(self, container: Tag) -> List[Player]:
        """Extract player information from HardRock format"""
        players = []
        
        # Look for participants container
        participants_container = container.select_one('.participants')
        if participants_container:
            # Extract individual participant divs
            participant_divs = participants_container.select('.participant')
            
            for participant_div in participant_divs:
                # Try both mobile and desktop versions
                name_elem = (participant_div.select_one('.hide-for-medsmall') or 
                           participant_div.select_one('.show-for-medsmall'))
                
                if name_elem:
                    player_name = name_elem.get_text(strip=True)
                    players.append(Player(name=player_name))
        
        # Fallback: look for vs pattern in text
        if len(players) < 2:
            text = container.get_text()
            vs_match = re.search(r'(.+?)\s+vs\s+(.+?)(?:\s|$)', text, re.IGNORECASE)
            if vs_match:
                player1_name = vs_match.group(1).strip()
                player2_name = vs_match.group(2).strip()
                
                # Clean up names
                player1_name = re.sub(r'[+-]\d+\.?\d*|@\d+\.?\d*|\d+/\d+', '', player1_name).strip()
                player2_name = re.sub(r'[+-]\d+\.?\d*|@\d+\.?\d*|\d+/\d+', '', player2_name).strip()
                
                players = [Player(name=player1_name), Player(name=player2_name)]
        
        return players
    
    def _extract_match_status(self, container: Tag) -> MatchStatus:
        """Determine if match is live or upcoming using HardRock indicators"""
        # Check for live icon
        live_icon = container.select_one('.live-icon')
        if live_icon:
            return MatchStatus.LIVE
        
        # Check for game status text
        game_status = container.select_one('.game-time-status')
        if game_status:
            status_text = game_status.get_text(strip=True).lower()
            if 'set' in status_text or 'game' in status_text:
                return MatchStatus.LIVE
        
        # Check for score containers (indicates live match)
        score_containers = container.select('.scoreContainer')
        if score_containers:
            # If we have scores and they're not all zeros, it's likely live
            for score_container in score_containers:
                scores = score_container.select('.score')
                if scores:
                    score_values = [s.get_text(strip=True) for s in scores]
                    # If any score is non-zero, it's live
                    if any(score != '0' for score in score_values if score.isdigit()):
                        return MatchStatus.LIVE
        
        # Default to upcoming
        return MatchStatus.UPCOMING
    
    def _extract_score(self, container: Tag) -> Optional[Score]:
        """Extract live match score from HardRock format"""
        score_containers = container.select('.scoreContainer')
        if not score_containers:
            return None
        
        try:
            # HardRock shows two score containers (one per player)
            all_sets = []
            current_set = 0
            
            # Extract main score (set wins)
            main_scores = []
            for score_container in score_containers:
                main_score_elem = score_container.select_one('.mainScore')
                if main_score_elem:
                    main_scores.append(main_score_elem.get_text(strip=True))
            
            # Extract individual set scores
            for score_container in score_containers:
                set_elements = score_container.select('.score:not(.mainScore)')
                player_set_scores = [elem.get_text(strip=True) for elem in set_elements]
                all_sets.append(player_set_scores)
            
            # Format set scores as "player1_score-player2_score"
            if len(all_sets) >= 2:
                set_scores = []
                max_sets = max(len(all_sets[0]), len(all_sets[1]))
                
                for i in range(max_sets):
                    score1 = all_sets[0][i] if i < len(all_sets[0]) else "0"
                    score2 = all_sets[1][i] if i < len(all_sets[1]) else "0"
                    if score1 != "0" or score2 != "0":  # Only include non-zero scores
                        set_scores.append(f"{score1}-{score2}")
                
                if set_scores:
                    # Current set is the number of completed sets + 1 if match is ongoing
                    current_set = len(set_scores)
                    
                    # Check if there's an ongoing set with partial scores
                    game_status = container.select_one('.game-time-status')
                    if game_status:
                        status_text = game_status.get_text(strip=True)
                        if 'set' in status_text.lower():
                            try:
                                set_num = int(re.search(r'(\d+)', status_text).group(1))
                                current_set = set_num
                            except:
                                pass
                    
                    return Score(
                        current_set=current_set,
                        set_scores=set_scores
                    )
        
        except Exception as e:
            self.logger.warning(f"Error parsing score: {e}")
        
        return None
    
    def _extract_odds(self, container: Tag) -> Optional[Odds]:
        """Extract betting odds from HardRock format"""
        odds = Odds()
        
        # Find selection containers
        selection_containers = container.select('.selection-container')
        
        player_odds = []
        for selection_container in selection_containers:
            # Check if this is a disabled/locked selection
            if selection_container.select_one('.empty-selection') or selection_container.select_one('.icon-lock-alt'):
                player_odds.append(None)  # Betting not available
            else:
                # Extract odds value
                odds_elem = selection_container.select_one('.selection-odds')
                if odds_elem:
                    odds_value = odds_elem.get_text(strip=True)
                    player_odds.append(odds_value)
                else:
                    player_odds.append(None)
        
        # Assign odds to players
        if len(player_odds) >= 2:
            odds.player1_moneyline = player_odds[0]
            odds.player2_moneyline = player_odds[1]
        elif len(player_odds) == 1:
            # Sometimes only one player has odds available
            odds.player1_moneyline = player_odds[0]
        
        # Fallback: look for odds patterns in text
        if not odds.player1_moneyline and not odds.player2_moneyline:
            text = container.get_text()
            odds_pattern = r'([+-]\d+)'
            odds_matches = re.findall(odds_pattern, text)
            
            if len(odds_matches) >= 2:
                odds.player1_moneyline = odds_matches[0]
                odds.player2_moneyline = odds_matches[1]
            elif len(odds_matches) == 1:
                odds.player1_moneyline = odds_matches[0]
        
        return odds if (odds.player1_moneyline or odds.player2_moneyline) else None
    
    def _extract_start_time(self, container: Tag) -> Optional[datetime]:
        """Extract match start time"""
        text = container.get_text()
        
        # Look for time patterns
        time_patterns = [
            r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)',
            r'(\d{1,2}/\d{1,2})',
            r'(Today|Tomorrow)'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # This would need more sophisticated parsing based on actual format
                # For now, return None and implement when we see actual data
                return None
        
        return None
    
    def _extract_league(self, container: Tag) -> Optional[str]:
        """Extract league/tournament information"""
        # Look for common table tennis league patterns
        text = container.get_text()
        
        tt_leagues = [
            'WTT', 'ITTF', 'Champions League', 'World Tour',
            'Pro Tour', 'Europa League', 'Asian Games'
        ]
        
        for league in tt_leagues:
            if league.lower() in text.lower():
                return league
        
        return None