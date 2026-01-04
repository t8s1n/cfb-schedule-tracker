"""
Configuration management for CFB Schedule Tracker.

Handles API keys, user preferences, and tracked teams/conferences.
"""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


def get_config_dir() -> Path:
    """Get the configuration directory, creating it if necessary."""
    config_dir = Path.home() / ".config" / "cfb-tracker"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get the data directory for cache and database files."""
    data_dir = Path.home() / ".local" / "share" / "cfb-tracker"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class TrackedTeams(BaseModel):
    """Configuration for which teams/conferences to track."""
    
    teams: list[str] = Field(default_factory=list, description="List of team names to track")
    conferences: list[str] = Field(default_factory=list, description="List of conference abbreviations")
    track_all_fbs: bool = Field(default=False, description="Track all FBS games")
    
    def is_empty(self) -> bool:
        """Check if no teams or conferences are being tracked."""
        return not self.teams and not self.conferences and not self.track_all_fbs


class CalendarSettings(BaseModel):
    """Settings for calendar output."""
    
    output_dir: Path = Field(
        default_factory=lambda: get_data_dir() / "calendars",
        description="Directory for ICS file output"
    )
    include_tv_info: bool = Field(default=True, description="Include TV broadcast info in events")
    include_venue: bool = Field(default=True, description="Include venue/location info")
    reminder_minutes: int = Field(default=60, description="Default reminder before game (minutes)")
    calendar_name: str = Field(default="CFB Schedule", description="Name of the calendar")
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True


class Config(BaseModel):
    """Main configuration for CFB Schedule Tracker."""
    
    cfbd_api_key: Optional[str] = Field(default=None, description="College Football Data API key")
    tracked: TrackedTeams = Field(default_factory=TrackedTeams)
    calendar: CalendarSettings = Field(default_factory=CalendarSettings)
    season: int = Field(default=2025, description="Current season year to track")
    
    class Config:
        """Pydantic config."""
        extra = "ignore"
        arbitrary_types_allowed = True
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file and environment."""
        config_file = get_config_dir() / "config.json"
        
        # Start with defaults
        config_data = {}
        
        # Load from file if exists
        if config_file.exists():
            with open(config_file, "r") as f:
                config_data = json.load(f)
        
        # Override API key from environment if set
        env_api_key = os.getenv("CFBD_API_KEY")
        if env_api_key:
            config_data["cfbd_api_key"] = env_api_key
        
        return cls(**config_data)
    
    def save(self) -> None:
        """Save configuration to file."""
        config_file = get_config_dir() / "config.json"
        
        # Don't save API key to file if it came from environment
        save_data = self.dict()
        if os.getenv("CFBD_API_KEY"):
            save_data.pop("cfbd_api_key", None)
        
        # Convert Path objects to strings for JSON serialization
        if "calendar" in save_data and "output_dir" in save_data["calendar"]:
            save_data["calendar"]["output_dir"] = str(save_data["calendar"]["output_dir"])
        
        with open(config_file, "w") as f:
            json.dump(save_data, f, indent=2)
    
    def has_api_key(self) -> bool:
        """Check if an API key is configured."""
        return bool(self.cfbd_api_key)


# FBS Conference abbreviations for reference
FBS_CONFERENCES = {
    "ACC": "Atlantic Coast Conference",
    "B12": "Big 12 Conference", 
    "B1G": "Big Ten Conference",
    "SEC": "Southeastern Conference",
    "PAC": "Pac-12 Conference",
    "AAC": "American Athletic Conference",
    "CUSA": "Conference USA",
    "IND": "FBS Independents",
    "MAC": "Mid-American Conference",
    "MWC": "Mountain West Conference",
    "SBC": "Sun Belt Conference",
}
