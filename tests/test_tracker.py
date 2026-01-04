"""
Tests for CFB Schedule Tracker.
"""

import pytest
from datetime import datetime
from pathlib import Path

from cfb_tracker.config import Config, TrackedTeams, FBS_CONFERENCES
from cfb_tracker.api import Game, validate_conference
from cfb_tracker.calendar import create_game_event, CalendarSettings


class TestConfig:
    """Tests for configuration module."""
    
    def test_tracked_teams_is_empty(self):
        """Test empty tracking detection."""
        tracked = TrackedTeams()
        assert tracked.is_empty()
        
        tracked.teams = ["Michigan"]
        assert not tracked.is_empty()
    
    def test_fbs_conferences_defined(self):
        """Test FBS conferences are properly defined."""
        assert "SEC" in FBS_CONFERENCES
        assert "B1G" in FBS_CONFERENCES
        assert "ACC" in FBS_CONFERENCES
        assert len(FBS_CONFERENCES) >= 10


class TestGame:
    """Tests for Game dataclass."""
    
    def get_sample_game(self) -> Game:
        """Create a sample game for testing."""
        return Game(
            id=12345,
            season=2025,
            week=1,
            season_type="regular",
            start_date=datetime(2025, 8, 30, 19, 30),
            start_time_tbd=False,
            neutral_site=False,
            conference_game=True,
            home_team="Michigan",
            home_conference="Big Ten",
            home_points=None,
            away_team="Ohio State",
            away_conference="Big Ten",
            away_points=None,
            venue="Michigan Stadium",
            venue_city="Ann Arbor",
            venue_state="MI",
            tv_network="ABC",
            notes=None,
        )
    
    def test_matchup_string(self):
        """Test matchup formatting."""
        game = self.get_sample_game()
        assert game.matchup == "Ohio State @ Michigan"
    
    def test_is_completed(self):
        """Test game completion detection."""
        game = self.get_sample_game()
        assert not game.is_completed
        
        game.home_points = 28
        game.away_points = 21
        assert game.is_completed
    
    def test_location_formatting(self):
        """Test location string formatting."""
        game = self.get_sample_game()
        assert "Michigan Stadium" in game.location
        assert "Ann Arbor" in game.location
        assert "MI" in game.location
    
    def test_involves_team(self):
        """Test team involvement check."""
        game = self.get_sample_game()
        assert game.involves_team("Michigan")
        assert game.involves_team("ohio state")  # Case insensitive
        assert not game.involves_team("Alabama")
    
    def test_involves_conference(self):
        """Test conference involvement check."""
        game = self.get_sample_game()
        assert game.involves_conference("Big Ten")
        assert game.involves_conference("big ten")  # Case insensitive
        assert not game.involves_conference("SEC")


class TestCalendar:
    """Tests for calendar generation."""
    
    def get_sample_game(self) -> Game:
        """Create a sample game for testing."""
        return Game(
            id=12345,
            season=2025,
            week=1,
            season_type="regular",
            start_date=datetime(2025, 8, 30, 19, 30),
            start_time_tbd=False,
            neutral_site=False,
            conference_game=True,
            home_team="Michigan",
            home_conference="Big Ten",
            home_points=None,
            away_team="Ohio State",
            away_conference="Big Ten",
            away_points=None,
            venue="Michigan Stadium",
            venue_city="Ann Arbor",
            venue_state="MI",
            tv_network="ABC",
            notes=None,
        )
    
    def test_create_game_event(self):
        """Test calendar event creation."""
        game = self.get_sample_game()
        settings = CalendarSettings()
        
        event = create_game_event(game, settings)
        
        assert event is not None
        assert "Ohio State @ Michigan" in str(event.get("summary"))
        assert event.get("location") is not None
    
    def test_game_without_date_returns_none(self):
        """Test that games without dates return None."""
        game = self.get_sample_game()
        game.start_date = None
        settings = CalendarSettings()
        
        event = create_game_event(game, settings)
        assert event is None
    
    def test_bowl_game_includes_notes(self):
        """Test that bowl games include notes in summary."""
        game = self.get_sample_game()
        game.notes = "Rose Bowl"
        settings = CalendarSettings()
        
        event = create_game_event(game, settings)
        
        assert "Rose Bowl" in str(event.get("summary"))


class TestValidation:
    """Tests for validation functions."""
    
    def test_validate_conference(self):
        """Test conference validation."""
        assert validate_conference("SEC") == "SEC"
        assert validate_conference("sec") == "SEC"
        assert validate_conference("B1G") == "B1G"
        assert validate_conference("Big Ten") == "B1G"
        assert validate_conference("Unknown") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
