from pydantic import BaseModel

class Opponent(BaseModel):
    name: str
    acronym: str
    location: str
