# CFB Schedule Tracker

Track college football games and sync them to your calendar. Generates ICS files compatible with Google Calendar, Apple Calendar, Outlook, and any other calendar app that supports the iCalendar format.

## Features

- Fetch game schedules from the College Football Data API
- Track specific teams, conferences, or all FBS games
- Generate ICS calendar files for easy import
- Include TV broadcast information and venue details
- Automatic game time reminders
- CLI interface for easy management

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/cfb-schedule-tracker.git
cd cfb-schedule-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

### Dependencies

- Python 3.10+
- cfbd (College Football Data API client)
- icalendar (ICS file generation)
- click (CLI framework)
- rich (Terminal formatting)

## Quick Start

### 1. Get an API Key

Register for a free API key at [collegefootballdata.com/key](https://collegefootballdata.com/key)

The free tier allows 1,000 API calls per month, which is plenty for personal use.

### 2. Initialize Configuration

```bash
cfb-tracker init
```

This will prompt you for:
- Your CFBD API key
- Season year to track
- Teams or conferences to follow

### 3. Generate Calendars

```bash
# Sync and generate calendar files
cfb-tracker sync

# Or generate for specific teams
cfb-tracker sync --team "Michigan" --team "Ohio State"

# Or for a conference
cfb-tracker sync --conference SEC
```

### 4. Import to Google Calendar

1. Go to [calendar.google.com](https://calendar.google.com)
2. Click the gear icon and select "Settings"
3. Go to "Import & Export"
4. Click "Import" and select your `.ics` file
5. Choose which calendar to add events to

## Usage

### Commands

```bash
# Initialize/setup
cfb-tracker init

# List available teams
cfb-tracker teams
cfb-tracker teams --search "Michigan"

# List conferences
cfb-tracker conferences

# Track teams/conferences
cfb-tracker track "Michigan"
cfb-tracker track SEC --conference

# Stop tracking
cfb-tracker untrack "Michigan"
cfb-tracker untrack SEC --conference

# View status
cfb-tracker status

# Generate calendars
cfb-tracker sync
cfb-tracker sync --all-fbs
cfb-tracker sync --team "Alabama" --season 2025

# View schedule
cfb-tracker schedule
cfb-tracker schedule --team "Michigan" --upcoming
cfb-tracker schedule --week 1
```

### Environment Variables

You can set your API key via environment variable instead of storing it in the config file:

```bash
export CFBD_API_KEY="your-api-key-here"
```

Or create a `.env` file in your project directory:

```
CFBD_API_KEY=your-api-key-here
```

## Configuration

Configuration is stored in `~/.config/cfb-tracker/config.json`

```json
{
  "season": 2025,
  "tracked": {
    "teams": ["Michigan", "Ohio State"],
    "conferences": ["B1G"],
    "track_all_fbs": false
  },
  "calendar": {
    "output_dir": "~/.local/share/cfb-tracker/calendars",
    "include_tv_info": true,
    "include_venue": true,
    "reminder_minutes": 60,
    "calendar_name": "CFB Schedule"
  }
}
```

## Calendar Files

Generated ICS files are saved to `~/.local/share/cfb-tracker/calendars/` by default:

- `cfb_schedule.ics` - Combined schedule for all tracked teams/conferences
- `cfb_michigan.ics` - Individual team schedule (when tracking specific teams)
- `cfb_b1g.ics` - Conference schedule (when tracking conferences)

## Updating Schedules

Game times are often announced or changed throughout the season. To update your calendars:

```bash
cfb-tracker sync
```

Then re-import the ICS file to your calendar app. Most calendar apps will update existing events rather than creating duplicates (based on the unique event ID).

### Automated Updates (Cron)

To automatically update weekly:

```bash
# Edit crontab
crontab -e

# Add line to sync every Sunday at 6am
0 6 * * 0 /path/to/venv/bin/cfb-tracker sync
```

## API Rate Limits

The CFBD API has the following rate limits:

| Tier | Monthly Calls | Cost |
|------|---------------|------|
| Free | 1,000 | $0 |
| Tier 1 | 10,000 | $5/mo |
| Tier 2 | 25,000 | $7/mo |
| Tier 3 | 75,000 | $10/mo |

A typical sync uses 2-5 API calls, so the free tier is sufficient for personal use.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/

# Type checking
mypy src/
```

## Future Features

- [ ] Google Calendar API direct sync (OAuth2)
- [ ] Apple Calendar integration
- [ ] Score notifications
- [ ] Game prediction tracking
- [ ] Web interface

## License

MIT License - see LICENSE file

## Acknowledgments

- [College Football Data](https://collegefootballdata.com/) for the excellent API
- [cfbd](https://github.com/CFBD/cfbd-python) Python client library
