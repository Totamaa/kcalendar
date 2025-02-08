from pydantic import BaseModel
from datetime import datetime, timedelta

class BaseMatch(BaseModel):
    id: str
    tournament_name: str
    tournament_slug: str
    tournament_tier: str
    videogame_name: str
    videogame_slug: str
    number_of_games: int
    begin_at: datetime 
    duration: timedelta
    slug: str
    league_name: str
    stream_url: str
