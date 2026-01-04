cat > README.md << 'EOF'
# CFB Schedule Tracker

Track college football games on your calendar with automatic updates.

## Subscribe to Calendar

Add to Google Calendar (or any calendar app):

1. Click `+` next to "Other calendars"
2. Select "From URL"
3. Paste: `https://t8s1n.github.io/cfb-schedule-tracker/cfb_maryland.ics`
4. Click "Add calendar"

The calendar auto-updates every 12-24 hours with:
- Game time changes
- New games (bowl games, playoffs)
- Final scores
- Venue updates

## Available Calendars

- `cfb_schedule.ics` - All tracked games
- `cfb_maryland.ics` - Maryland Terrapins

## How It Works

1. GitHub Actions runs daily at 6am UTC
2. Pulls latest schedule from [College Football Data API](https://collegefootballdata.com/)
3. Generates ICS calendar files
4. Publishes to GitHub Pages
5. Your calendar app fetches updates automatically

## Local Development

### Setup
```bash
git clone https://github.com/t8s1n/cfb-schedule-tracker.git
cd cfb-schedule-tracker
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Get API Key

Register for free at [collegefootballdata.com/key](https://collegefootballdata.com/key)
```bash
export CFBD_API_KEY="your-key-here"
```

### Commands
```bash
cfb-tracker init              # Setup wizard
cfb-tracker teams             # List FBS teams
cfb-tracker teams -s "Mich"   # Search teams
cfb-tracker conferences       # List conferences
cfb-tracker track "Michigan"  # Track a team
cfb-tracker track SEC -c      # Track a conference
cfb-tracker untrack "Michigan"
cfb-tracker status            # Show config
cfb-tracker sync              # Generate calendars
cfb-tracker schedule          # View upcoming games
cfb-tracker schedule --team "Maryland" --upcoming
```

## Fork Your Own

1. Fork this repo
2. Add secret `CFBD_API_KEY` in Settings > Secrets > Actions
3. Add variable `CFB_TRACKER_CONFIG` with your teams:
```json
   {"season": 2025, "tracked": {"teams": ["Your Team"], "conferences": [], "track_all_fbs": false}}
```
4. Enable GitHub Pages (Settings > Pages > main branch, /docs folder)
5. Run the workflow manually or wait for daily run

## License

MIT
EOF
