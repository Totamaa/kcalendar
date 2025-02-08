from pydantic import BaseModel
from typing import List
from schemas.base_match import BaseMatch
from schemas.player import Player

class MatchMulti(BaseMatch):
    players: list[Player]  # Une liste d'objets Player
