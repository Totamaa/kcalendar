from datetime import timedelta
import requests

from box import Box

from config.logs import LoggerManager
from config.settings import get_settings
from enums.game_mapping import GAME_FORMAT_MAPPING, GameFormat
from enums.game_parser import GAME_API_PARSER_MAPPING, GameApiParser
from schemas.match_duo import MatchDuo
from schemas.match_multi import MatchMulti

class EsportAPIService:
    def __init__(self):
        # Initialize logger and settings
        self.logging = LoggerManager()
        settings = get_settings()
        self.base_url = settings.BACK_PANDA_BASE_URL
        self.api_key = settings.BACK_PANDA_API_KEY

    def fetch_matches_for_team(self, team_id):
        """Fetch and normalize matches for a given team, handling pagination."""
        url = f"{self.base_url}/teams/{team_id}/matches?filter[status]=not_started&sort=begin_at&page="
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        matches = []
        page = 1
        
        self.logging.info(f"Starting to fetch matches for team {team_id}.")
        
        while True:
            paginated_url = f"{url}{page}"
            self.logging.info(f"Fetching page {page} from URL: {paginated_url}")
            
            try:
                response = requests.get(paginated_url, headers=headers)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as e:
                self.logging.error(f"Error fetching matches from page {page}: {e}")
                break
            
            if not data:  # If no data is returned, we break out of the loop
                self.logging.info(f"No more matches found for team {team_id} on page {page}.")
                break
            
            # Process each match in the response
            for match_json in data:
                match = Box(match_json)
                game_slug = match.videogame.slug
                
                # Select the API parser based on the game type
                parser_key = GAME_API_PARSER_MAPPING.get(game_slug, GameApiParser.DUO)
                # Map the parser key to the corresponding function
                api_parser_mapping = {
                    GameApiParser.DUO: self._api_parse_duo,
                    GameApiParser.RL: self._api_parse_rl,
                    GameApiParser.MULTI: self._api_parse_multi,
                }
                parser = api_parser_mapping.get(parser_key, self._api_parse_duo)
                match_obj = parser(match)
                if match_obj:
                    matches.append(match_obj)
            
            page += 1  # Increment the page for the next request
        
        return matches

    def _api_parse_duo(self, match):
        """Parse matches for duo team games (e.g., LoL, VALO)."""
        stream = next(
            (s for s in match.streams_list if s.main and s.language == 'fr'),
            next((s for s in match.streams_list if s.main), None)
        )
        stream_url = stream.raw_url if stream else ""
        
        opponents = [
            {
                "acronym": match.opponents[0].opponent.acronym,
                "name": match.opponents[0].opponent.name,
                "location": match.opponents[0].opponent.location,
            },
            {
                "acronym": match.opponents[1].opponent.acronym,
                "name": match.opponents[1].opponent.name,
                "location": match.opponents[1].opponent.location,
            }
        ]
        
        # Duration based on the number of games
        if match.number_of_games == 5:
            duration = timedelta(hours=3)
        elif match.number_of_games == 3:
            duration = timedelta(hours=2)
        else:
            duration = timedelta(hours=1)
        
        # Return the parsed match object
        return MatchDuo(
            id=f"{match.league_id}{match.tournament_id}{match.serie_id}{match.id}",
            tournament_name=match.tournament.name,
            tournament_slug=match.tournament.slug,
            tournament_tier=match.tournament.tier,
            videogame_name=match.videogame.name,
            videogame_slug=match.videogame.slug,
            begin_at=match.begin_at,
            number_of_games=match.number_of_games,
            opponents=opponents,
            slug=match.slug,
            league_name=match.league.name,
            stream_url=stream_url,
            duration=duration
        )

    def _api_parse_rl(self, match):
        """Parse Rocket League matches."""
        stream = next(
            (s for s in match.streams_list if s.main and s.language == 'fr'),
            next((s for s in match.streams_list if s.main), None)
        )
        stream_url = stream.raw_url if stream else ""
        
        opponents = [
            {
                "acronym": match.opponents[0].opponent.acronym,
                "name": match.opponents[0].opponent.name,
                "location": match.opponents[0].opponent.location,
            },
            {
                "acronym": match.opponents[1].opponent.acronym,
                "name": match.opponents[1].opponent.name,
                "location": match.opponents[1].opponent.location,
            }
        ]
        
        # Duration for Rocket League matches based on number of games
        if match.number_of_games == 5:
            duration = timedelta(hours=1)
        elif match.number_of_games == 7:
            duration = timedelta(minutes=90) # Average time for a BO7
        else:
            duration = timedelta(hours=1)
        
        # Return the parsed match object
        return MatchDuo(
            id=f"{match.league_id}{match.tournament_id}{match.serie_id}{match.id}",
            tournament_name=match.tournament.name,
            tournament_slug=match.tournament.slug,
            tournament_tier=match.tournament.tier,
            videogame_name=match.videogame.name,
            videogame_slug=match.videogame.slug,
            begin_at=match.begin_at,
            number_of_games=match.number_of_games,
            opponents=opponents,
            slug=match.slug,
            league_name=match.league.name,
            stream_url=stream_url,
            duration=duration
        )

    def _api_parse_multi(self, match):
        """Parse multi-player games (e.g., Fortnite, TFT)."""
        stream = next(
            (s for s in match.streams_list if s.main and s.language == 'fr'),
            next((s for s in match.streams_list if s.main), None)
        )
        stream_url = stream.raw_url if stream else ""
        players = match.players if hasattr(match, 'players') else []
        duration = timedelta(hours=1) # Default duration for multi-player games
        return MatchMulti(
            id=f"{match.league_id}{match.tournament_id}{match.serie_id}{match.id}",
            tournament_name=match.tournament.name,
            tournament_slug=match.tournament.slug,
            tournament_tier=match.tournament.tier,
            videogame_name=match.videogame.name,
            videogame_slug=match.videogame.slug.lower(),
            begin_at=match.begin_at,
            number_of_games=match.number_of_games,
            players=players,
            slug=match.slug,
            league_name=match.league.name,
            stream_url=stream_url,
            duration=duration
        )
