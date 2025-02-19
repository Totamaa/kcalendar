from pydantic import BaseModel

class Opponent(BaseModel):
    name: str
    acronym: str | None = None
    location: str | None = None
