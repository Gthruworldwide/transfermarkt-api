from typing import Annotated

from fastapi import Query

PageNumber = Annotated[int, Query(ge=1, le=10_000, description="1-based page number (maximum 10000).")]
SeasonId = Annotated[str, Query(pattern=r"^[0-9]+$", description="Numeric season identifier, e.g. 2024.")]
