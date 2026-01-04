"""
Command-line interface for CFB Schedule Tracker.

Usage:
    cfb-tracker init           # Set up API key and initial config
    cfb-tracker teams          # List available teams
    cfb-tracker track          # Add teams/conferences to track
    cfb-tracker untrack        # Remove teams/conferences from tracking
    cfb-tracker status         # Show current configuration
    cfb-tracker sync           # Fetch schedule and generate calendars
    cfb-tracker schedule       # View upcoming games
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from . import __version__
from .config import Config, FBS_CONFERENCES, get_config_dir, get_data_dir
from .api import CFBDClient, get_fbs_team_names, validate_team_name, validate_conference
from .calendar import CalendarManager, generate_schedule_calendar


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()


def get_client(config: Config) -> Optional[CFBDClient]:
    """Get an API client, prompting for key if not configured."""
    if not config.has_api_key():
        console.print("[red]No API key configured.[/red]")
        console.print("Run [bold]cfb-tracker init[/bold] to set up your API key.")
        return None
    
    return CFBDClient(config.cfbd_api_key)


@click.group()
@click.version_option(version=__version__)
def main():
    """
    CFB Schedule Tracker - Track college football games on your calendar.
    
    Get started with: cfb-tracker init
    """
    pass


@main.command()
def init():
    """Initialize configuration and set up API key."""
    console.print(Panel.fit(
        "[bold]CFB Schedule Tracker Setup[/bold]\n\n"
        "This will configure your API key and initial settings.",
        title="Welcome"
    ))
    
    config = Config.load()
    
    # Check for existing config
    if config.has_api_key():
        if not Confirm.ask("API key already configured. Overwrite?"):
            console.print("Setup cancelled.")
            return
    
    # Get API key
    console.print("\n[bold]Step 1: API Key[/bold]")
    console.print("Get your free API key from: [link]https://collegefootballdata.com/key[/link]")
    console.print("The free tier allows 1,000 API calls per month.\n")
    
    api_key = Prompt.ask("Enter your CFBD API key")
    
    if not api_key.strip():
        console.print("[red]No API key provided. Setup cancelled.[/red]")
        return
    
    # Test the API key
    console.print("\nTesting API key...", end=" ")
    test_client = CFBDClient(api_key.strip())
    if test_client.check_api_key():
        console.print("[green]Valid![/green]")
    else:
        console.print("[red]Invalid API key. Please check and try again.[/red]")
        return
    
    config.cfbd_api_key = api_key.strip()
    
    # Set season
    console.print("\n[bold]Step 2: Season[/bold]")
    current_year = datetime.now().year
    default_season = current_year if datetime.now().month >= 8 else current_year
    season = Prompt.ask(
        "Which season to track?",
        default=str(default_season)
    )
    config.season = int(season)
    
    # Track all FBS or specific teams
    console.print("\n[bold]Step 3: What to Track[/bold]")
    console.print("Options:")
    console.print("  1. All FBS games (generates large calendar)")
    console.print("  2. Specific teams")
    console.print("  3. Specific conferences")
    console.print("  4. Configure later\n")
    
    choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4"], default="4")
    
    if choice == "1":
        config.tracked.track_all_fbs = True
        console.print("[green]Configured to track all FBS games.[/green]")
    elif choice == "2":
        console.print("\nEnter team names (comma-separated):")
        console.print("Example: Michigan, Ohio State, Alabama")
        teams_input = Prompt.ask("Teams")
        if teams_input.strip():
            teams = [t.strip() for t in teams_input.split(",")]
            # Validate team names
            valid_teams = []
            for team in teams:
                validated = validate_team_name(test_client, team)
                if validated:
                    valid_teams.append(validated)
                    console.print(f"  [green]+ {validated}[/green]")
                else:
                    console.print(f"  [yellow]? '{team}' not found, skipping[/yellow]")
            config.tracked.teams = valid_teams
    elif choice == "3":
        console.print("\nAvailable conferences:")
        for abbrev, name in FBS_CONFERENCES.items():
            console.print(f"  {abbrev}: {name}")
        console.print("\nEnter conference abbreviations (comma-separated):")
        conf_input = Prompt.ask("Conferences")
        if conf_input.strip():
            confs = [c.strip().upper() for c in conf_input.split(",")]
            valid_confs = [c for c in confs if c in FBS_CONFERENCES]
            config.tracked.conferences = valid_confs
            for c in valid_confs:
                console.print(f"  [green]+ {c}[/green]")
    
    # Save configuration
    config.save()
    
    console.print("\n[green]Configuration saved![/green]")
    console.print(f"Config file: {get_config_dir() / 'config.json'}")
    console.print(f"Data directory: {get_data_dir()}")
    console.print("\nNext steps:")
    console.print("  - Run [bold]cfb-tracker sync[/bold] to fetch schedule and generate calendars")
    console.print("  - Run [bold]cfb-tracker track <team>[/bold] to add more teams")
    console.print("  - Run [bold]cfb-tracker status[/bold] to see current configuration")


@main.command()
@click.option("--search", "-s", help="Search for teams containing this text")
def teams(search: Optional[str]):
    """List available FBS teams."""
    config = Config.load()
    client = get_client(config)
    if not client:
        return
    
    console.print("Fetching teams...\n")
    team_names = get_fbs_team_names(client)
    
    if search:
        search_lower = search.lower()
        team_names = [t for t in team_names if search_lower in t.lower()]
        console.print(f"Teams matching '{search}':\n")
    
    # Display in columns
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column()
    table.add_column()
    table.add_column()
    
    # Split into 3 columns
    col_size = (len(team_names) + 2) // 3
    for i in range(col_size):
        row = []
        for j in range(3):
            idx = i + j * col_size
            if idx < len(team_names):
                row.append(team_names[idx])
            else:
                row.append("")
        table.add_row(*row)
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(team_names)} teams[/dim]")


@main.command()
def conferences():
    """List FBS conferences."""
    table = Table(title="FBS Conferences")
    table.add_column("Abbreviation", style="bold")
    table.add_column("Full Name")
    
    for abbrev, name in sorted(FBS_CONFERENCES.items()):
        table.add_row(abbrev, name)
    
    console.print(table)


@main.command()
@click.argument("name")
@click.option("--conference", "-c", is_flag=True, help="Track a conference instead of team")
def track(name: str, conference: bool):
    """Add a team or conference to track."""
    config = Config.load()
    
    if conference:
        # Validate conference
        validated = validate_conference(name)
        if not validated:
            console.print(f"[red]Unknown conference: {name}[/red]")
            console.print("Use [bold]cfb-tracker conferences[/bold] to see available options.")
            return
        
        if validated in config.tracked.conferences:
            console.print(f"[yellow]Already tracking {validated}[/yellow]")
            return
        
        config.tracked.conferences.append(validated)
        config.save()
        console.print(f"[green]Now tracking {validated} ({FBS_CONFERENCES[validated]})[/green]")
    else:
        # Validate team
        client = get_client(config)
        if not client:
            return
        
        validated = validate_team_name(client, name)
        if not validated:
            console.print(f"[red]Unknown team: {name}[/red]")
            console.print("Use [bold]cfb-tracker teams --search <name>[/bold] to search.")
            return
        
        if validated in config.tracked.teams:
            console.print(f"[yellow]Already tracking {validated}[/yellow]")
            return
        
        config.tracked.teams.append(validated)
        config.save()
        console.print(f"[green]Now tracking {validated}[/green]")


@main.command()
@click.argument("name")
@click.option("--conference", "-c", is_flag=True, help="Untrack a conference instead of team")
def untrack(name: str, conference: bool):
    """Remove a team or conference from tracking."""
    config = Config.load()
    
    if conference:
        name_upper = name.upper()
        if name_upper in config.tracked.conferences:
            config.tracked.conferences.remove(name_upper)
            config.save()
            console.print(f"[green]Stopped tracking {name_upper}[/green]")
        else:
            console.print(f"[yellow]Not currently tracking {name_upper}[/yellow]")
    else:
        # Find matching team (case-insensitive)
        name_lower = name.lower()
        matched = None
        for team in config.tracked.teams:
            if team.lower() == name_lower:
                matched = team
                break
        
        if matched:
            config.tracked.teams.remove(matched)
            config.save()
            console.print(f"[green]Stopped tracking {matched}[/green]")
        else:
            console.print(f"[yellow]Not currently tracking {name}[/yellow]")


@main.command()
def status():
    """Show current configuration and tracking status."""
    config = Config.load()
    
    console.print(Panel.fit("[bold]CFB Schedule Tracker Status[/bold]"))
    
    # API Key status
    if config.has_api_key():
        console.print("[green]API Key: Configured[/green]")
    else:
        console.print("[red]API Key: Not configured[/red]")
    
    # Season
    console.print(f"Season: {config.season}")
    
    # Tracking status
    console.print("\n[bold]Tracking:[/bold]")
    if config.tracked.track_all_fbs:
        console.print("  [cyan]All FBS games[/cyan]")
    elif config.tracked.teams or config.tracked.conferences:
        if config.tracked.teams:
            console.print("  Teams:")
            for team in sorted(config.tracked.teams):
                console.print(f"    - {team}")
        if config.tracked.conferences:
            console.print("  Conferences:")
            for conf in sorted(config.tracked.conferences):
                console.print(f"    - {conf} ({FBS_CONFERENCES.get(conf, 'Unknown')})")
    else:
        console.print("  [yellow]Nothing configured - run 'cfb-tracker track <team>'[/yellow]")
    
    # Calendar settings
    console.print(f"\n[bold]Calendar Output:[/bold]")
    console.print(f"  Directory: {config.calendar.output_dir}")
    console.print(f"  Include TV info: {config.calendar.include_tv_info}")
    console.print(f"  Include venue: {config.calendar.include_venue}")
    console.print(f"  Reminder: {config.calendar.reminder_minutes} minutes before")
    
    # Check for existing calendar files
    if config.calendar.output_dir.exists():
        ics_files = list(config.calendar.output_dir.glob("*.ics"))
        if ics_files:
            console.print(f"\n[bold]Generated Calendars:[/bold]")
            for f in sorted(ics_files):
                console.print(f"  {f.name}")


@main.command()
@click.option("--team", "-t", multiple=True, help="Generate calendar for specific team(s)")
@click.option("--conference", "-c", multiple=True, help="Generate calendar for specific conference(s)")
@click.option("--all-fbs", is_flag=True, help="Generate calendar for all FBS games")
@click.option("--season", "-s", type=int, help="Season year (default: configured season)")
def sync(team: tuple, conference: tuple, all_fbs: bool, season: Optional[int]):
    """Fetch schedule and generate calendar files."""
    config = Config.load()
    client = get_client(config)
    if not client:
        return
    
    season_year = season or config.season
    
    # Determine what to track
    teams_to_track = list(team) if team else config.tracked.teams
    confs_to_track = list(conference) if conference else config.tracked.conferences
    track_all = all_fbs or config.tracked.track_all_fbs
    
    if not track_all and not teams_to_track and not confs_to_track:
        console.print("[yellow]Nothing to track. Use --team, --conference, or --all-fbs[/yellow]")
        console.print("Or run [bold]cfb-tracker track <team>[/bold] to configure.")
        return
    
    # Fetch games
    console.print(f"Fetching {season_year} schedule...")
    
    try:
        if track_all:
            games = client.get_season_games(year=season_year)
        else:
            games = client.get_season_games(
                year=season_year,
                teams=teams_to_track if teams_to_track else None,
                conferences=confs_to_track if confs_to_track else None,
            )
    except Exception as e:
        console.print(f"[red]Failed to fetch games: {e}[/red]")
        return
    
    console.print(f"Found {len(games)} games")
    
    # Generate calendars
    console.print("Generating calendar files...")
    
    manager = CalendarManager(config.calendar)
    
    try:
        generated = manager.generate_all(
            games=games,
            teams=teams_to_track if teams_to_track else None,
            conferences=confs_to_track if confs_to_track else None,
            generate_master=True,
        )
    except Exception as e:
        console.print(f"[red]Failed to generate calendars: {e}[/red]")
        return
    
    console.print(f"\n[green]Generated {len(generated)} calendar file(s):[/green]")
    for path in generated:
        console.print(f"  {path}")
    
    console.print("\n[bold]To import into Google Calendar:[/bold]")
    console.print("  1. Go to calendar.google.com")
    console.print("  2. Click the gear icon > Settings")
    console.print("  3. Import & Export > Import")
    console.print("  4. Select the .ics file and choose a calendar")


@main.command()
@click.option("--team", "-t", help="Show schedule for specific team")
@click.option("--conference", "-c", help="Show schedule for specific conference")
@click.option("--week", "-w", type=int, help="Show specific week")
@click.option("--upcoming", "-u", is_flag=True, help="Show only upcoming games")
@click.option("--limit", "-n", type=int, default=20, help="Maximum games to show")
def schedule(
    team: Optional[str],
    conference: Optional[str],
    week: Optional[int],
    upcoming: bool,
    limit: int
):
    """View game schedule."""
    config = Config.load()
    client = get_client(config)
    if not client:
        return
    
    # Fetch games
    try:
        games = client.get_season_games(
            year=config.season,
            teams=[team] if team else None,
            conferences=[conference] if conference else None,
        )
    except Exception as e:
        console.print(f"[red]Failed to fetch games: {e}[/red]")
        return
    
    # Filter by week
    if week:
        games = [g for g in games if g.week == week]
    
    # Filter upcoming
    if upcoming:
        now = datetime.now()
        games = [g for g in games if g.start_date and g.start_date > now]
    
    # Limit results
    games = games[:limit]
    
    if not games:
        console.print("[yellow]No games found matching criteria.[/yellow]")
        return
    
    # Display table
    table = Table(title=f"{config.season} CFB Schedule")
    table.add_column("Week", style="dim")
    table.add_column("Date")
    table.add_column("Matchup")
    table.add_column("TV", style="cyan")
    table.add_column("Score")
    
    for game in games:
        # Format date
        if game.start_date:
            if game.start_time_tbd:
                date_str = game.start_date.strftime("%a %b %d") + " TBD"
            else:
                date_str = game.start_date.strftime("%a %b %d %I:%M%p")
        else:
            date_str = "TBD"
        
        # Format score
        if game.is_completed:
            score = f"{game.away_points}-{game.home_points}"
        else:
            score = "-"
        
        table.add_row(
            str(game.week),
            date_str,
            game.matchup,
            game.tv_network or "-",
            score,
        )
    
    console.print(table)
    
    if len(games) == limit:
        console.print(f"\n[dim]Showing first {limit} games. Use --limit to see more.[/dim]")


@main.command()
@click.argument("output", type=click.Path(), required=False)
def export(output: Optional[str]):
    """Export current tracking configuration."""
    config = Config.load()
    
    export_data = {
        "season": config.season,
        "tracked": {
            "teams": config.tracked.teams,
            "conferences": config.tracked.conferences,
            "track_all_fbs": config.tracked.track_all_fbs,
        }
    }
    
    import json
    
    if output:
        with open(output, "w") as f:
            json.dump(export_data, f, indent=2)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(json.dumps(export_data, indent=2))


@main.command()
def debug():
    """Debug: show raw API response for first game."""
    import cfbd
    config = Config.load()
    if not config.has_api_key():
        console.print("[red]No API key[/red]")
        return
    
    configuration = cfbd.Configuration(access_token=config.cfbd_api_key)
    with cfbd.ApiClient(configuration) as api_client:
        games_api = cfbd.GamesApi(api_client)
        games = games_api.get_games(year=2025, classification="fbs")
        if games:
            g = games[0]
            console.print(f"Type: {type(g)}")
            console.print(f"Dict: {g.to_dict()}")


if __name__ == "__main__":
    main()
