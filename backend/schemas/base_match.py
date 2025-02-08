from pydantic import BaseModel
from datetime import datetime

class BaseMatch(BaseModel):
    id: str
    tournament_name: str
    tournament_slug: str
    tournament_tier: str
    videogame_name: str
    videogame_slug: str
    begin_at: datetime  # Auto-parsable en datetime
    number_of_games: int
    slug: str
    league_name: str
    stream_url: str
