from typing import Annotated

from fastapi import Path, Query

PageNumber = Annotated[int, Query(ge=1, le=10_000, description="1-based page number (maximum 10000).")]
SeasonId = Annotated[str, Query(pattern=r"^[0-9]+$", description="Numeric season identifier, e.g. 2024.")]
EntityId = Annotated[str, Path(pattern=r"^[0-9]+$", description="Numeric entity identifier, e.g. 28003.")]
CompetitionId = Annotated[str, Path(pattern=r"^[A-Za-z0-9]+$", description="Competition code, e.g. GB1, ES1 or CL.")]
