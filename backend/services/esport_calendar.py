import os
import shutil
import time
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event, vText
from config.logs import LoggerManager
from enums.game_mapping import GAME_FORMAT_MAPPING, GameFormat
from services.esport_api import EsportAPIService
from schemas.match_duo import MatchDuo
from schemas.match_multi import MatchMulti

class EsportCalendarService:
    def __init__(self):
        # Initialize logger, API service and team IDs for fetching matches
        self.logging = LoggerManager()
        self.api_service = EsportAPIService()
        self.team_ids = [
            134078,  # LOL KC
            128268,  # LOL KC blue
            136080,  # LOL KC blue stars
            130922,  # VALO KC
            132777,  # VALO KC GC
            136165,  # VALO KC Blue stars
            129570,  # Rocket League
        ]
        self.static_dir = "static"
        self.ics_file_path = os.path.join(self.static_dir, "calendar.ics")
        self.temp_ics_file_path = os.path.join(self.static_dir, "calendar_temp.ics")
        os.makedirs(self.static_dir, exist_ok=True)

    def update_calendar(self):
        """Fetch matches and update the ICS calendar file."""
        self.logging.info("Starting calendar update process...")
        start_time = time.perf_counter()

        matches = []
        for team_id in self.team_ids:
            self.logging.info(f"Fetching matches for team ID: {team_id}")
            matches.extend(self.api_service.fetch_matches_for_team(team_id))

        if matches:
            self._generate_calendar_events(matches)
            self._replace_calendar_atomically()
            self.logging.info(f"Calendar updated with {len(matches)} matches.")
        else:
            self.logging.warning("No matches fetched.")

        elapsed = time.perf_counter() - start_time
        self.logging.info(f"Calendar update completed in {elapsed} seconds.")

    def _load_existing_calendar(self):
        """Load the existing calendar or create a new one if it doesn't exist."""
        if os.path.exists(self.ics_file_path):
            try:
                with open(self.ics_file_path, 'rb') as f:
                    return Calendar.from_ical(f.read())
            except Exception as e:
                self.logging.error(f"Error loading calendar: {e}")
                
        # Create a new calendar if none exists
        cal = Calendar()
        cal.add('version', '2.0')
        cal.add('prodid', '-//esport calendar//')
        cal.add('calscale', 'GREGORIAN')
        cal.add('x-wr-calname', 'Esport Matches')
        return cal

    def _generate_calendar_events(self, matches):
        """Generate or update ICS events from the fetched matches."""
        cal = self._load_existing_calendar()
        existing_uids = {comp.get('uid') for comp in cal.walk('vevent') if comp.get('uid')}

        for match in matches:
            # Generate events matches
            if isinstance(match, MatchDuo):
                event = self._calendar_event_duo(match)
            elif isinstance(match, MatchMulti):
                event = self._calendar_event_multi(match)
            else:
                event = self._calendar_event_duo(match)
            uid = event.get('uid')
            # Remove existing event if the UID already exists
            if uid in existing_uids:
                cal.subcomponents = [
                    comp for comp in cal.subcomponents
                    if not (comp.name == "VEVENT" and comp.get('uid') == uid)
                ]
            cal.add_component(event)

        with open(self.temp_ics_file_path, 'wb') as f:
            f.write(cal.to_ical())
        self.logging.info("Temporary calendar file generated.")

    def _replace_calendar_atomically(self):
        """Replace the old calendar file with the new one atomically."""
        try:
            shutil.move(self.temp_ics_file_path, self.ics_file_path)
            self.logging.info("Calendar file updated successfully.")
        except Exception as e:
            self.logging.error(f"Error replacing calendar file: {e}")
            if os.path.exists(self.temp_ics_file_path):
                os.remove(self.temp_ics_file_path)

    def _calendar_event_duo(self, match: MatchDuo):
        """Create an ICS event for a duo-team match."""
        uid = f"{match.id}@esport_calendar"
        event = Event()
        event.add('uid', uid)
        opp1, opp2 = match.opponents
        summary = f"[{match.league_name}] {opp1.name} vs {opp2.name} ({match.tournament_name} BO{match.number_of_games})"
        event.add('summary', summary)

        # Event description with match details
        description = (
            f"Video Game: [{match.videogame_slug}] {match.videogame_name}\n"
            f"League: {match.league_name}\n"
            f"Tournament: [Tier {match.tournament_tier}] {match.tournament_slug}\n"
            f"Match: {match.slug}\n"
            f"Team 1: [{opp1.location}] {opp1.name} ({opp1.acronym})\n"
            f"Team 2: [{opp2.location}] {opp2.name} ({opp2.acronym})"
        )
        event.add('description', description)

        # Ensure time is in UTC if not already
        start_time = match.begin_at
        if not start_time.tzinfo:
            start_time = pytz.UTC.localize(start_time)
        event.add('dtstart', start_time)
        
        event.add('duration', match.duration)
        event.add('location', vText(match.stream_url))
        
        return event

    def _calendar_event_multi(self, match: MatchMulti):
        """Create an ICS event for a multi-player match."""
        uid = f"{match.id}@esport_calendar"
        event = Event()
        event.add('uid', uid)
        summary = f"[{match.league_name}] {match.slug}"
        event.add('summary', summary)

        # Event description for multi-player matches
        description = (
            f"Video Game: [{match.videogame_slug}] {match.videogame_name}\n"
            f"League: {match.league_name}\n"
            f"Tournament: [Tier {match.tournament_tier}] {match.tournament_slug}\n"
            f"Match: {match.slug}\n"
            "Multi-player match details."
        )
        event.add('description', description)

        start_time = datetime.fromisoformat(match.begin_at)
        if not start_time.tzinfo:
            start_time = pytz.UTC.localize(start_time)
        event.add('dtstart', start_time)
        event.add('duration', match.duration)
        event.add('location', vText(match.stream_url))
        return event
