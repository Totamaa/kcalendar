from enum import Enum

class GameFormat(Enum):
    TWO_TEAM = "two_team"
    MULTI_PLAYER = "multi_player"

# Mapping du slug du jeu vers son format.
GAME_FORMAT_MAPPING = {
    "league-of-legends": GameFormat.TWO_TEAM,
    "valorant": GameFormat.TWO_TEAM,
    "rocketleague": GameFormat.TWO_TEAM,
    # Pour le futur (exemple) :
    # "fortnite": GameFormat.MULTI_PLAYER,
    # "tft": GameFormat.MULTI_PLAYER,
}