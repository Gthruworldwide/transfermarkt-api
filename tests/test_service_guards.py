"""Defense-in-depth guards at the service layer for direct SDK-internal callers."""

import pytest

from transfermarkt_api.services.clubs.players import get_club_players

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio."""
    return "asyncio"


class HistoricalClubClient:
    """Minimal tfmkt client stub returning a squad with a non-current member."""

    async def attributes(self) -> dict:
        """Reference data needed by the squad assembler."""
        return {"countries": [{"id": 9, "name": "Argentina"}]}

    async def club_squad(self, club_id: str, season_id: str | None = None) -> dict:
        """A squad with one loaned player; the season is recorded upstream, not interpreted here."""
        return {"clubId": club_id, "squad": [{"playerId": "10", "type": "loan"}]}

    async def players(self, ids: list[str]) -> dict:
        """Player records keyed by ID."""
        return {player_id: {"id": player_id, "name": "Loaned Player"} for player_id in ids}

    async def player_transfer_history(self, player_id: str) -> dict:
        """No completed transfers."""
        return {"history": {"terminated": []}}

    async def clubs(self, ids: list[str]) -> dict:
        """No club records are needed for this squad."""
        return {}


@pytest.mark.parametrize("season_id", ["not-a-year", "2024x", "-1"])
async def test_service_ignores_non_numeric_season_instead_of_raising(season_id: str) -> None:
    """A direct service call cannot trigger an unhandled int() conversion with a malformed season."""
    result = await get_club_players(HistoricalClubClient(), "1", season_id)

    assert result["id"] == "1"
    assert [entry["name"] for entry in result["players"]] == ["Loaned Player"]
