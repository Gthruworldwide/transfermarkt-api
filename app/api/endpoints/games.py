from fastapi import APIRouter

from app.api.dependencies import Tfmkt
from app.api.params import EntityId
from transfermarkt_api.schemas.games import Game

router = APIRouter()


@router.get("/{game_id}")
async def get_game(game_id: EntityId, tfmkt: Tfmkt) -> Game:
    """Get a match: score, lineups, coaches, stadium and events (goals, cards, substitutions)."""
    return await tfmkt.game(game_id)
