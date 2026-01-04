"""
CFBD API client for fetching college football schedule data.

Uses the official cfbd Python package for API v2.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import cfbd
from cfbd.rest import ApiException

from .config import Config, FBS_CONFERENCES


logger = logging.getLogger(__name__)


@dataclass
class Game:
    """Normalized game data structure."""
    
    id: int
    season: int
    week: int
    season_type: str  # "regular" or "postseason"
    start_date: Optional[datetime]
    start_time_tbd: bool
    neutral_site: bool
    conference_game: bool
    
    home_team: str
    home_conference: Optional[str]
    home_points: Optional[int]
    
    away_team: str
    away_conference: Optional[str]
    away_points: Optional[int]
    
    venue: Optional[str]
    venue_city: Optional[str]
    venue_state: Optional[str]
    
    tv_network: Optional[str]
    notes: Optional[str]
    
    @property
    def is_completed(self) -> bool:
        """Check if the game has been completed."""
        return self.home_points is not None and self.away_points is not None
    
    @property
    def matchup(self) -> str:
        """Get a formatted matchup string."""
        return f"{self.away_team} @ {self.home_team}"
    
    @property
    def location(self) -> Optional[str]:
        """Get formatted location string."""
        parts = []
        if self.venue:
            parts.append(self.venue)
        if self.venue_city:
            city_state = self.venue_city
            if self.venue_state:
                city_state += f", {self.venue_state}"
            parts.append(city_state)
        return " - ".join(parts) if parts else None
    
    def involves_team(self, team: str) -> bool:
        """Check if a team is playing in this game."""
        team_lower = team.lower()
        home_lower = self.home_team.lower()
        away_lower = self.away_team.lower()
        return (
            team_lower in home_lower or home_lower in team_lower or
            team_lower in away_lower or away_lower in team_lower
        )
    
    def involves_conference(self, conference: str) -> bool:
        """Check if a conference team is playing in this game."""
        conf_lower = conference.lower()
        return (
            (self.home_conference and self.home_conference.lower() == conf_lower) or
            (self.away_conference and self.away_conference.lower() == conf_lower)
        )


class CFBDClient:
    """Client for interacting with the College Football Data API."""
    
    def __init__(self, api_key: str):
        """Initialize the CFBD client with an API key."""
        self.configuration = cfbd.Configuration(
            access_token=api_key
        )
        self._teams_cache: dict[str, dict] = {}
        self._conferences_cache: list[dict] = []
    
    def _get_api_client(self):
        """Get a configured API client context manager."""
        return cfbd.ApiClient(self.configuration)
    
    def get_teams(self, classification: str = "fbs") -> list[dict]:
        """
        Fetch all teams for a given classification.
        
        Args:
            classification: "fbs", "fcs", or "ii" / "iii"
        
        Returns:
            List of team dictionaries
        """
        cache_key = classification
        if cache_key in self._teams_cache:
            return list(self._teams_cache[cache_key].values())
        
        with self._get_api_client() as api_client:
            teams_api = cfbd.TeamsApi(api_client)
            try:
                teams = teams_api.get_teams()
                # Filter by classification and build cache
                self._teams_cache[cache_key] = {}
                for team in teams:
                    team_dict = team.to_dict()
                    team_class = team_dict.get("classification") or ""
                    if team_class.lower() == classification.lower():
                        self._teams_cache[cache_key][team_dict["school"].lower()] = team_dict
                
                logger.info(f"Fetched {len(self._teams_cache[cache_key])} {classification.upper()} teams")
                return list(self._teams_cache[cache_key].values())
            except ApiException as e:
                logger.error(f"Failed to fetch teams: {e}")
                raise
    
    def get_conferences(self) -> list[dict]:
        """Fetch all conferences."""
        if self._conferences_cache:
            return self._conferences_cache
        
        with self._get_api_client() as api_client:
            conferences_api = cfbd.ConferencesApi(api_client)
            try:
                conferences = conferences_api.get_conferences()
                self._conferences_cache = [conf.to_dict() for conf in conferences]
                logger.info(f"Fetched {len(self._conferences_cache)} conferences")
                return self._conferences_cache
            except ApiException as e:
                logger.error(f"Failed to fetch conferences: {e}")
                raise
    
    def get_games(
        self,
        year: int,
        week: Optional[int] = None,
        team: Optional[str] = None,
        conference: Optional[str] = None,
        season_type: str = "regular",
        classification: str = "fbs"
    ) -> list[Game]:
        """
        Fetch games with optional filters.
        
        Args:
            year: Season year
            week: Optional week number
            team: Optional team name filter
            conference: Optional conference abbreviation filter
            season_type: "regular" or "postseason"
            classification: "fbs" or "fcs"
        
        Returns:
            List of Game objects
        """
        with self._get_api_client() as api_client:
            games_api = cfbd.GamesApi(api_client)
            
            try:
                # Build kwargs for the API call
                kwargs = {
                    "year": year,
                    "classification": classification,
                }
                
                if week is not None:
                    kwargs["week"] = week
                if team:
                    kwargs["team"] = team
                if conference:
                    kwargs["conference"] = conference
                if season_type:
                    kwargs["season_type"] = season_type
                
                api_games = games_api.get_games(**kwargs)
                
                games = []
                for g in api_games:
                    game_dict = g.to_dict()
                    
                    # Parse start date
                    start_date = game_dict.get("startDate")
                    if start_date and isinstance(start_date, str):
                        try:
                            start_date = start_date.replace("Z", "+00:00")
                            start_date = datetime.fromisoformat(start_date)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Could not parse date: {e}")
                            start_date = None
                    
                    # Handle seasonType enum
                    season_type_val = game_dict.get("seasonType")
                    if hasattr(season_type_val, "value"):
                        season_type_val = season_type_val.value
                    
                    game = Game(
                        id=game_dict.get("id", 0),
                        season=game_dict.get("season", year),
                        week=game_dict.get("week", 0),
                        season_type=season_type_val or "regular",
                        start_date=start_date,
                        start_time_tbd=game_dict.get("startTimeTBD", False),
                        neutral_site=game_dict.get("neutralSite", False),
                        conference_game=game_dict.get("conferenceGame", False),
                        home_team=game_dict.get("homeTeam", ""),
                        home_conference=game_dict.get("homeConference"),
                        home_points=game_dict.get("homePoints"),
                        away_team=game_dict.get("awayTeam", ""),
                        away_conference=game_dict.get("awayConference"),
                        away_points=game_dict.get("awayPoints"),
                        venue=game_dict.get("venue"),
                        venue_city=None,
                        venue_state=None,
                        tv_network=None,
                        notes=game_dict.get("notes"),
                    )
                    games.append(game)
                
                logger.info(f"Fetched {len(games)} games for {year} {season_type}")
                return games
                
            except ApiException as e:
                logger.error(f"Failed to fetch games: {e}")
                raise
    
    def get_game_media(self, year: int, week: Optional[int] = None) -> dict[int, str]:
        """
        Fetch TV/streaming info for games.
        
        Returns:
            Dictionary mapping game_id to TV network string
        """
        with self._get_api_client() as api_client:
            games_api = cfbd.GamesApi(api_client)
            
            try:
                kwargs = {"year": year}
                if week is not None:
                    kwargs["week"] = week
                
                media_list = games_api.get_game_media(**kwargs)
                
                media_map = {}
                for m in media_list:
                    media_dict = m.to_dict()
                    game_id = media_dict.get("id")
                    outlet = media_dict.get("outlet")
                    if game_id and outlet:
                        media_map[game_id] = outlet
                
                logger.info(f"Fetched media info for {len(media_map)} games")
                return media_map
                
            except ApiException as e:
                logger.error(f"Failed to fetch game media: {e}")
                return {}
    
    def get_calendar(self, year: int) -> list[dict]:
        """
        Fetch the season calendar (weeks and dates).
        
        Returns:
            List of week dictionaries with start/end dates
        """
        with self._get_api_client() as api_client:
            games_api = cfbd.GamesApi(api_client)
            
            try:
                calendar = games_api.get_calendar(year=year)
                return [week.to_dict() for week in calendar]
            except ApiException as e:
                logger.error(f"Failed to fetch calendar: {e}")
                raise
    
    def get_season_games(
        self,
        year: int,
        teams: Optional[list[str]] = None,
        conferences: Optional[list[str]] = None,
        include_postseason: bool = True,
        classification: str = "fbs"
    ) -> list[Game]:
        """
        Fetch all games for a season with optional team/conference filters.
        
        This is the main method for fetching a complete schedule.
        
        Args:
            year: Season year
            teams: List of team names to filter by
            conferences: List of conference abbreviations to filter by
            include_postseason: Whether to include bowl games
            classification: "fbs" or "fcs"
        
        Returns:
            List of Game objects matching the filters
        """
        all_games = []
        
        # Fetch regular season
        regular_games = self.get_games(
            year=year,
            season_type="regular",
            classification=classification
        )
        all_games.extend(regular_games)
        
        # Fetch postseason if requested
        if include_postseason:
            try:
                postseason_games = self.get_games(
                    year=year,
                    season_type="postseason",
                    classification=classification
                )
                all_games.extend(postseason_games)
            except ApiException:
                # Postseason might not be available yet
                logger.info("Postseason games not yet available")
        
        # Fetch media info for TV networks (skip if method not available)
        try:
            media_map = self.get_game_media(year=year)
            for game in all_games:
                if game.id in media_map:
                    game.tv_network = media_map[game.id]
        except (ApiException, AttributeError):
            logger.warning("Could not fetch media info - continuing without TV data")
        
        # Filter by teams if specified
        if teams:
            teams_lower = [t.lower() for t in teams]
            filtered = []
            for g in all_games:
                home_lower = g.home_team.lower()
                away_lower = g.away_team.lower()
                for t in teams_lower:
                    if t in home_lower or home_lower in t or t in away_lower or away_lower in t:
                        filtered.append(g)
                        break
            all_games = filtered
        
        # Filter by conferences if specified
        if conferences:
            conf_lower = [c.lower() for c in conferences]
            all_games = [
                g for g in all_games
                if (g.home_conference and g.home_conference.lower() in conf_lower) or
                   (g.away_conference and g.away_conference.lower() in conf_lower)
            ]
        
        # Sort by date
        all_games.sort(key=lambda g: (g.start_date or datetime.max, g.week))
        
        logger.info(f"Returning {len(all_games)} filtered games")
        return all_games
    
    def check_api_key(self) -> bool:
        """Verify the API key is valid by making a test request."""
        try:
            # Simple test - fetch conferences (low overhead)
            self.get_conferences()
            return True
        except ApiException as e:
            if e.status == 401:
                logger.error("Invalid API key")
            else:
                logger.error(f"API error: {e}")
            return False
    
    def get_remaining_calls(self) -> Optional[int]:
        """
        Get the remaining API calls for this month.
        
        Note: This requires parsing response headers which isn't directly
        available through the standard client. Returns None if unavailable.
        """
        # The cfbd package doesn't expose headers easily
        # For now, return None - users should check the CFBD dashboard
        return None


def get_fbs_team_names(client: CFBDClient) -> list[str]:
    """Get a sorted list of all FBS team names."""
    teams = client.get_teams(classification="fbs")
    return sorted([t["school"] for t in teams])


def validate_team_name(client: CFBDClient, team: str) -> Optional[str]:
    """
    Validate and normalize a team name.
    
    Returns the correct team name if found, None otherwise.
    """
    teams = client.get_teams(classification="fbs")
    team_lower = team.lower()
    
    for t in teams:
        school = t["school"]
        # Check exact match (case-insensitive)
        if school.lower() == team_lower:
            return school
        # Check if input is a substring (for common abbreviations)
        if team_lower in school.lower():
            return school
        # Check mascot match
        mascot = t.get("mascot", "")
        if mascot and team_lower == mascot.lower():
            return school
    
    return None


def validate_conference(conference: str) -> Optional[str]:
    """
    Validate a conference abbreviation.
    
    Returns the correct abbreviation if valid, None otherwise.
    """
    conf_upper = conference.upper()
    if conf_upper in FBS_CONFERENCES:
        return conf_upper
    
    # Check by full name
    for abbrev, full_name in FBS_CONFERENCES.items():
        if conference.lower() in full_name.lower():
            return abbrev
    
    return None
