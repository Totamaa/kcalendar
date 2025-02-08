from pydantic import BaseModel
from typing import List
from schemas.base_match import BaseMatch
from schemas.opponent import Opponent

class MatchDuo(BaseMatch):
    opponents: list[Opponent]  # Une liste d'objets Opponent
