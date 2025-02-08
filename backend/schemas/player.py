from pydantic import BaseModel

class Player(BaseModel):
    name: str
    team_name: str | None = None  # Optionnel (pour les jeux solo)
    country: str
