"""
Calendar generation for CFB Schedule Tracker.

Generates ICS files compatible with Google Calendar, Apple Calendar, Outlook, etc.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, Alarm

from .api import Game
from .config import CalendarSettings


logger = logging.getLogger(__name__)


# Default timezone for games (most CFB games are in US timezones)
DEFAULT_TIMEZONE = ZoneInfo("America/New_York")

# Typical game duration for calendar events
GAME_DURATION_HOURS = 4


def generate_event_uid(game: Game) -> str:
    """Generate a unique, stable UID for a game event."""
    # Use game ID and season for stable UID across updates
    uid_source = f"cfb-{game.season}-{game.id}"
    return hashlib.md5(uid_source.encode()).hexdigest() + "@cfb-tracker"


def create_game_event(
    game: Game,
    settings: CalendarSettings,
) -> Optional[Event]:
    """
    Create an iCalendar event for a game.
    
    Args:
        game: Game object with schedule data
        settings: Calendar settings for customization
    
    Returns:
        Event object or None if game has no valid date
    """
    if not game.start_date:
        logger.warning(f"Game {game.matchup} has no start date, skipping")
        return None
    
    event = Event()
    
    # Generate stable UID
    event.add("uid", generate_event_uid(game))
    
    # Summary (title)
    if game.notes:
        # Bowl games and special events
        summary = f"{game.notes}: {game.matchup}"
    else:
        summary = game.matchup
    event.add("summary", summary)
    
    # Start and end time
    start_dt = game.start_date
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=DEFAULT_TIMEZONE)
    
    if game.start_time_tbd:
        # All-day event if time is TBD
        event.add("dtstart", start_dt.date())
        event.add("dtend", start_dt.date() + timedelta(days=1))
    else:
        event.add("dtstart", start_dt)
        event.add("dtend", start_dt + timedelta(hours=GAME_DURATION_HOURS))
    
    # Location
    if settings.include_venue and game.location:
        event.add("location", game.location)
    
    # Description
    description_parts = []
    
    # Conference info
    if game.conference_game:
        description_parts.append("Conference Game")
    if game.neutral_site:
        description_parts.append("Neutral Site")
    
    # Team conferences
    if game.away_conference:
        description_parts.append(f"{game.away_team} ({game.away_conference})")
    else:
        description_parts.append(game.away_team)
    description_parts.append("at")
    if game.home_conference:
        description_parts.append(f"{game.home_team} ({game.home_conference})")
    else:
        description_parts.append(game.home_team)
    
    # TV info
    if settings.include_tv_info and game.tv_network:
        description_parts.append(f"\nTV: {game.tv_network}")
    
    # Week info
    description_parts.append(f"\nWeek {game.week} - {game.season} {game.season_type.title()}")
    
    # Score if completed
    if game.is_completed:
        score = f"\nFinal: {game.away_team} {game.away_points} - {game.home_team} {game.home_points}"
        description_parts.append(score)
    
    event.add("description", " ".join(description_parts))
    
    # Categories
    categories = ["College Football", "CFB"]
    if game.conference_game:
        categories.append("Conference")
    if game.season_type == "postseason":
        categories.append("Bowl Game")
    event.add("categories", categories)
    
    # Reminder/Alarm
    if settings.reminder_minutes > 0 and not game.start_time_tbd:
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", f"Game starting soon: {game.matchup}")
        alarm.add("trigger", timedelta(minutes=-settings.reminder_minutes))
        event.add_component(alarm)
    
    # Timestamps
    event.add("dtstamp", datetime.now(tz=DEFAULT_TIMEZONE))
    event.add("created", datetime.now(tz=DEFAULT_TIMEZONE))
    
    return event


def create_calendar(
    games: list[Game],
    settings: CalendarSettings,
    calendar_name: Optional[str] = None,
) -> Calendar:
    """
    Create an iCalendar object from a list of games.
    
    Args:
        games: List of Game objects
        settings: Calendar settings
        calendar_name: Optional override for calendar name
    
    Returns:
        Calendar object ready for export
    """
    cal = Calendar()
    
    # Calendar metadata
    cal.add("prodid", "-//CFB Schedule Tracker//cfb-tracker//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name or settings.calendar_name)
    cal.add("x-wr-timezone", str(DEFAULT_TIMEZONE))
    
    # Add events
    events_added = 0
    for game in games:
        event = create_game_event(game, settings)
        if event:
            cal.add_component(event)
            events_added += 1
    
    logger.info(f"Created calendar with {events_added} events")
    return cal


def export_calendar(
    cal: Calendar,
    output_path: Path,
) -> Path:
    """
    Export a calendar to an ICS file.
    
    Args:
        cal: Calendar object to export
        output_path: Path for the output file
    
    Returns:
        Path to the created file
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write calendar to file
    with open(output_path, "wb") as f:
        f.write(cal.to_ical())
    
    logger.info(f"Exported calendar to {output_path}")
    return output_path


def generate_schedule_calendar(
    games: list[Game],
    settings: CalendarSettings,
    filename: str = "cfb_schedule.ics",
    calendar_name: Optional[str] = None,
) -> Path:
    """
    Generate and export a calendar file from games.
    
    This is the main high-level function for calendar generation.
    
    Args:
        games: List of Game objects
        settings: Calendar settings
        filename: Output filename
        calendar_name: Optional calendar name override
    
    Returns:
        Path to the generated ICS file
    """
    # Ensure output directory exists
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create calendar
    cal = create_calendar(games, settings, calendar_name)
    
    # Export to file
    output_path = settings.output_dir / filename
    return export_calendar(cal, output_path)


def generate_team_calendar(
    games: list[Game],
    team: str,
    settings: CalendarSettings,
) -> Path:
    """
    Generate a calendar for a specific team.
    
    Args:
        games: List of all games (will be filtered)
        team: Team name to filter by
        settings: Calendar settings
    
    Returns:
        Path to the generated ICS file
    """
    # Filter games for this team
    team_games = [g for g in games if g.involves_team(team)]
    
    # Generate safe filename
    safe_name = team.lower().replace(" ", "_").replace("&", "and")
    filename = f"cfb_{safe_name}.ics"
    calendar_name = f"{team} Football Schedule"
    
    return generate_schedule_calendar(
        games=team_games,
        settings=settings,
        filename=filename,
        calendar_name=calendar_name,
    )


def generate_conference_calendar(
    games: list[Game],
    conference: str,
    settings: CalendarSettings,
) -> Path:
    """
    Generate a calendar for a conference.
    
    Args:
        games: List of all games (will be filtered)
        conference: Conference abbreviation
        settings: Calendar settings
    
    Returns:
        Path to the generated ICS file
    """
    # Filter games involving conference teams
    conf_games = [g for g in games if g.involves_conference(conference)]
    
    # Generate filename
    filename = f"cfb_{conference.lower()}.ics"
    calendar_name = f"{conference} Football Schedule"
    
    return generate_schedule_calendar(
        games=conf_games,
        settings=settings,
        filename=filename,
        calendar_name=calendar_name,
    )


class CalendarManager:
    """
    Manager for generating and updating calendar files.
    
    Handles multiple calendars (by team, conference, or all FBS).
    """
    
    def __init__(self, settings: CalendarSettings):
        self.settings = settings
        self._generated_files: list[Path] = []
    
    def generate_all(
        self,
        games: list[Game],
        teams: Optional[list[str]] = None,
        conferences: Optional[list[str]] = None,
        generate_master: bool = True,
    ) -> list[Path]:
        """
        Generate all configured calendars.
        
        Args:
            games: List of all games
            teams: Optional list of teams to generate individual calendars for
            conferences: Optional list of conferences to generate calendars for
            generate_master: Whether to generate a combined master calendar
        
        Returns:
            List of paths to generated files
        """
        generated = []
        
        # Generate team calendars
        if teams:
            for team in teams:
                try:
                    path = generate_team_calendar(games, team, self.settings)
                    generated.append(path)
                except Exception as e:
                    logger.error(f"Failed to generate calendar for {team}: {e}")
        
        # Generate conference calendars
        if conferences:
            for conf in conferences:
                try:
                    path = generate_conference_calendar(games, conf, self.settings)
                    generated.append(path)
                except Exception as e:
                    logger.error(f"Failed to generate calendar for {conf}: {e}")
        
        # Generate master calendar
        if generate_master:
            # Filter games based on tracked teams/conferences
            filtered_games = games
            if teams or conferences:
                filtered_games = [
                    g for g in games
                    if (teams and any(g.involves_team(t) for t in teams)) or
                       (conferences and any(g.involves_conference(c) for c in conferences))
                ]
            
            try:
                path = generate_schedule_calendar(
                    games=filtered_games,
                    settings=self.settings,
                    filename="cfb_schedule.ics",
                    calendar_name=self.settings.calendar_name,
                )
                generated.append(path)
            except Exception as e:
                logger.error(f"Failed to generate master calendar: {e}")
        
        self._generated_files = generated
        return generated
    
    @property
    def output_files(self) -> list[Path]:
        """Get list of generated calendar files."""
        return self._generated_files
