import time
import requests
from datetime import datetime, timedelta
import os
import shutil

from icalendar import Calendar, Event, vText, vUri
import pytz
from box import Box

from config.logs import LoggerManager
from config.settings import get_settings
 
class EsportCalendarService:
    def __init__(self):
        # Initialize the service with configuration
        self.logging = LoggerManager()
        settings = get_settings()
        self.base_url = settings.BACK_PANDA_BASE_URL
        self.api_key = settings.BACK_PANDA_API_KEY
        self.team_ids = [
            134078, # LOL KC
            128268, # LOL KC blue
            136080, # LOL KC blue stars
            130922, # VALO KC
            132777, # VALO KC GC
            136165, # VALO KC Blue stars
            129570, # RL
        ]
        self.static_dir = "static"  # Directory to save the .ics file
        self.ics_file_path = os.path.join(self.static_dir, "calendar.ics")  # Path to the final .ics file
        self.temp_ics_file_path = os.path.join(self.static_dir, "calendar_temp.ics")  # Temp file path for atomic update
 
        # Ensure the static directory exists
        os.makedirs(self.static_dir, exist_ok=True)
 
    def _fetch_upcoming_matches(self, team_id):
        """Fetch upcoming match data from the PandaScore API"""
        url = f"{self.base_url}/teams/{team_id}/matches?filter[status]=not_started&sort=begin_at"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        self.logging.info(f"Fetching upcoming matches from API... URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception if the request fails
            data = response.json()
        except requests.RequestException as e:
            self.logging.error(f"Error fetching matches: {e}")
            return []
 
        matches = []
        for match_json in data:
            match = Box(match_json)
            stream = next(
                (s for s in match.streams_list if s.main and s.language == 'fr'),
                next((s for s in match.streams_list if s.main), None)
            )
            match.stream_url = stream.raw_url if stream else ""
            
            matches.append({
                "id": f"{match.league_id}{match.tournament_id}{match.serie_id}{match.id}",
                "tournament_name": match.tournament.name,
                "tournament_slug": match.tournament.slug,
                "tournament_tier": match.tournament.tier,
                "videogame_name": match.videogame.name,
                "videogame_slug": match.videogame.slug,
                "begin_at": match.begin_at,
                "number_of_games": match.number_of_games,
                "opponents_1_acronym": match.opponents[0].opponent.acronym,
                "opponents_1_name": match.opponents[0].opponent.name,
                "opponents_1_location": match.opponents[0].opponent.location,
                "opponents_2_acronym": match.opponents[1].opponent.acronym,
                "opponents_2_name": match.opponents[1].opponent.name,
                "opponents_2_location": match.opponents[1].opponent.location,
                "slug": match.slug,
                "league_name": match.league.name,
                "stream_url": match.stream_url,
            })
            
            self.logging.info(f"Fetched match: {match.slug} at {datetime.fromisoformat(match.begin_at)} from tournament {match.tournament.slug}")
            
        return matches
    
    def _parse_match_lol_valo(self):
        raise NotImplementedError("Not implemented yet")
    
    def _parse_match_rl(self):
        raise NotImplementedError("Not implemented yet")
 
    def _load_existing_calendar(self):
        """Load the existing .ics calendar file if it exists, otherwise return a new calendar"""
        if os.path.exists(self.ics_file_path):
            try:
                with open(self.ics_file_path, 'rb') as f:
                    self.logging.info(f"Loaded existing calendar file: {self.ics_file_path}")
                    return Calendar.from_ical(f.read())
            except Exception as e:
                self.logging.error(f"Error loading existing calendar: {e}")
                return self._create_new_calendar()
        
        self.logging.info("No existing calendar file found. Creating a new calendar.")
        return self._create_new_calendar()
 
    def _create_new_calendar(self):
        """Create a new calendar with default properties"""
        calendar = Calendar()
        calendar.add('version', '2.0')
        calendar.add('prodid', '-//kcalendar.eu//Esport Calendar//EN')
        calendar.add('calscale', 'GREGORIAN')
        calendar.add('x-wr-calname', 'Esports Matches')
        return calendar
 
    def _generate_calendar_events(self, matches):
        """Generate calendar events from the match data and update the .ics calendar"""
        calendar = self._load_existing_calendar()
        
        # Garder une trace des événements existants
        existing_events = {}
        for component in calendar.walk('vevent'):
            uid = component.get('uid')
            if uid:
                existing_events[uid] = component
 
        for match in matches:
            match = Box(match)
            event_uid = f"{match.id}@esport_calendar"
            
            # Créer un nouvel événement
            event = Event()
            
            # Configurer l'événement
            event.add('uid', event_uid)
            event.add('summary', f"[{match.league_name}] {match.opponents_1_name} - {match.opponents_2_name} ({match.tournament_name} BO{match.number_of_games})")
            
            # Description détaillée
            description = (
                f"Video Game: [{match.videogame_name}] {match.videogame_slug}\n"
                f"League: {match.league_name}\n"
                f"Tournament: [Tier {match.tournament_tier}] {match.tournament_slug}\n"
                f"Match: {match.slug}\n"
                f"Team 1: [{match.opponents_1_location}] {match.opponents_1_name} ({match.opponents_1_acronym})\n"
                f"Team 2: [{match.opponents_2_location}] {match.opponents_2_name} ({match.opponents_2_acronym})"
            )
            event.add('description', description)
            
            # Gérer la date et la durée
            start_time = datetime.fromisoformat(match.begin_at)
            if not start_time.tzinfo:
                start_time = pytz.UTC.localize(start_time)
            event.add('dtstart', start_time)
            
            # Définir la durée selon le nombre de matchs
            if match.number_of_games == 5:
                duration = timedelta(hours=3)
            elif match.number_of_games == 3:
                duration = timedelta(hours=2)
            else:
                duration = timedelta(hours=1)
            event.add('duration', duration)
            
            # Ajouter l'URL du stream
            event.add('location', vText(match.stream_url))
 
            # Mettre à jour ou ajouter l'événement
            if event_uid in existing_events:
                self.logging.info(f"Updating event: {match.opponents_1_name} vs {match.opponents_2_name}")
                calendar.subcomponents = [
                    c for c in calendar.subcomponents 
                    if not (isinstance(c, Event) and c.get('uid') == event_uid)
                ]
            else:
                self.logging.info(f"Adding event: {match.opponents_1_name} vs {match.opponents_2_name}")
            
            calendar.add_component(event)
 
        # Sauvegarder dans le fichier temporaire
        with open(self.temp_ics_file_path, 'wb') as f:
            f.write(calendar.to_ical())
        
            self.logging.info(f"Temporary calendar file {self.temp_ics_file_path} generated.")
 
    def _replace_calendar_atomically(self):
        """Replace the existing .ics file atomically with the updated one"""
        try:
            # Atomically replace the old calendar with the new one
            shutil.move(self.temp_ics_file_path, self.ics_file_path)
            self.logging.info(f"Successfully updated the calendar file: {self.ics_file_path}.")
        except Exception as e:
            self.logging.error(f"Error updating the ICS file: {e}")
            # If something goes wrong, make sure to clean up the temporary file
            if os.path.exists(self.temp_ics_file_path):
                os.remove(self.temp_ics_file_path)
 
    def update_calendar(self):
        """Main method to update the calendar"""
        self.logging.info("Starting calendar update process...")
        start_time = time.perf_counter()
    
        matches = []
        for team_id in self.team_ids:
            self.logging.info(f"Fetching upcoming matches for team ID: {team_id}")
            matches.extend(self._fetch_upcoming_matches(team_id))
    
        log_nb_fetch_match = f"Total matches fetched: {len(matches)}"
        
        if matches:
            self.logging.info(log_nb_fetch_match)
            self._generate_calendar_events(matches)  # Generate events based on fetched data
            self._replace_calendar_atomically()  # Replace the old calendar with the new one
        else:
            self.logging.warning(log_nb_fetch_match)
    
        process_time = time.perf_counter() - start_time
        self.logging.info(f"Calendar update process completed. (time: {process_time})")