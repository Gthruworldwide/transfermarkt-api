import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "path",
    [
        "/players/abc/profile",
        "/players/-1/stats",
        "/players/12x/transfers",
        "/clubs/abc/profile",
        "/clubs/12x/players",
        "/coaches/abc/profile",
        "/games/abc",
    ],
)
def test_numeric_entity_ids_must_be_digits(client: TestClient, path: str) -> None:
    """Non-numeric path IDs are rejected by the route before any upstream call."""
    assert client.get(path).status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/competitions/GB-1/clubs",
        "/competitions/GB_1/table",
        "/competitions/GB%201/seasons",
    ],
)
def test_competition_codes_are_alphanumeric(client: TestClient, path: str) -> None:
    """Competition codes accept only letters and digits."""
    assert client.get(path).status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/competitions/GB1/clubs?season_id=abcd",
        "/competitions/GB1/table?season_id=2024x",
        "/players/28003/matches?season_id=not-a-year",
    ],
)
def test_season_ids_must_be_digits(client: TestClient, path: str) -> None:
    """Season query parameters follow the same numeric allowlist on every route."""
    assert client.get(path).status_code == 422


def test_valid_competition_code_still_routes(client: TestClient) -> None:
    """The allowlist admits real competition codes."""
    assert client.get("/competitions/GB1/seasons").status_code == 200
