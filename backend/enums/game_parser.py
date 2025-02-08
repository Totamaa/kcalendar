from enum import Enum

class GameApiParser(Enum):
    DUO = "duo"
    RL = "rl"
    MULTI = "multi"
    
GAME_API_PARSER_MAPPING = {
    "league-of-legends": GameApiParser.DUO,
    "valorant": GameApiParser.DUO,
    "rocketleague": GameApiParser.RL,  # Même si pour l'instant le parser est identique à "duo", on le sépare pour pouvoir évoluer.
    # "fortnite": GameApiParser.MULTI,
    # "tft": GameApiParser.MULTI,
}