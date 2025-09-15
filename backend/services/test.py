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
        """
        Initialize the EsportCalendarService.
        
        Sets up the internal logger and API service, configures the list of team IDs whose matches will be fetched, and establishes filesystem paths for the calendar files. Ensures the static directory exists.
        
        Attributes:
            logging: LoggerManager instance used for service logging.
            api_service: EsportAPIService used to fetch match data.
            team_ids (list[int]): Numeric IDs for teams to fetch matches for.
            static_dir (str): Directory where calendar files are stored.
            ics_file_path (str): Path to the primary calendar file (calendar.ics).
            temp_ics_file_path (str): Path to the temporary calendar file used for atomic updates (calendar_temp.ics).
        """
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
        """
        Load and return the existing iCalendar file, or create and return a new Calendar if the file is missing or cannot be parsed.
        
        If the ICS file at self.ics_file_path exists, attempts to parse and return it as an icalendar.Calendar. If the file does not exist or parsing fails, returns a newly constructed Calendar populated with standard properties:
        - version '2.0'
        - prodid '-//esport calendar//'
        - calscale 'GREGORIAN'
        - x-wr-calname 'Esport Matches'
        
        Returns:
            icalendar.Calendar: The loaded or newly created calendar object.
        """
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
        """
        Generate or update calendar VEVENTs from a list of match objects and write the result to the temporary ICS file.
        
        Loads the existing calendar (or creates a new one), converts each match into an ical Event (using _calendar_event_duo or _calendar_event_multi depending on the match type), and ensures there are no duplicate events by UID: if an event with the same UID already exists it is replaced. The resulting calendar is written in binary iCal format to self.temp_ics_file_path.
        
        Parameters:
            matches (Iterable[MatchDuo | MatchMulti]): Iterable of match objects to convert into calendar events. Each item should be an instance the service recognizes (MatchDuo or MatchMulti); unrecognized types are treated as duo matches.
        
        Side effects:
            - Reads the existing calendar via _load_existing_calendar().
            - Writes the updated calendar to the temporary ICS file at self.temp_ics_file_path.
        """
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
        """
        Atomically replace the main calendar file with the temporary calendar file.
        
        Moves self.temp_ics_file_path to self.ics_file_path. If the move fails, the temporary file is removed if present to avoid leaving a stale temp file. Exceptions are handled internally (no exception is propagated).
        """
        try:
            shutil.move(self.temp_ics_file_path, self.ics_file_path)
            self.logging.info("Calendar file updated successfully.")
        except Exception as e:
            self.logging.error(f"Error replacing calendar file: {e}")
            if os.path.exists(self.temp_ics_file_path):
                os.remove(self.temp_ics_file_path)

    def _calendar_event_duo(self, match: MatchDuo):
        """
        Create an iCalendar VEVENT for a two-team (duo) match.
        
        Builds an Event with a stable UID ("<match.id>@esport_calendar"), a summary in the form
        "[<league_name>] <team1> vs <team2> (<tournament_name> BO<n>)", and a multiline description
        containing videogame, league, tournament, match slug, and both teams' location/name/acronym.
        
        The event's start time (dtstart) is ensured to be timezone-aware; if the match begin_at has no
        tzinfo it is localized to UTC. The event also sets duration and location (stream URL).
        
        Parameters:
            match (MatchDuo): Match object for a duo-team match; expected to provide at least
                id, opponents (two objects with name/location/acronym), league_name, tournament_name,
                tournament_tier, tournament_slug, videogame_slug, videogame_name, slug,
                begin_at (datetime), duration (timedelta), and stream_url.
        
        Returns:
            icalendar.event.Event: The constructed VEVENT ready to be added to a Calendar.
        """
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
        """
        Create an iCalendar VEVENT for a multi-player match.
        
        Builds and returns an icalendar.Event with:
        - uid set to "<match.id>@esport_calendar"
        - summary in the form "[<league_name>] <slug>"
        - a multiline description containing videogame, league, tournament tier/slug and match slug
        - dtstart parsed from match.begin_at (ISO 8601 string). If the parsed datetime is naive, it is localized to UTC.
        - duration set from match.duration
        - location set to the match stream URL
        
        Parameters:
            match (MatchMulti): Match object where
                - match.begin_at is an ISO 8601 datetime string,
                - match.duration is a datetime.timedelta,
                - match.stream_url is a string URL.
        
        Returns:
            icalendar.Event: The constructed VEVENT ready to be added to a Calendar.
        """
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
