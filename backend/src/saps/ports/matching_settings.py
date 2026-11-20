"""Persistence port of the matching settings use case (SAPS-28)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.matching import MatchingRules


@dataclass(frozen=True)
class MatchingSettingsView:
    rules: MatchingRules
    updated_at: datetime
    updated_by: str
    """Display name of the user who changed the settings; `system` for the defaults of the seed."""


class MatchingSettingsRepository(Protocol):
    async def get(self, tenant_id: UUID) -> MatchingSettingsView: ...

    async def lock(self, tenant_id: UUID) -> MatchingSettingsView:
        """Read the settings and hold the row until the transaction ends (EC-04)."""
        ...

    async def save(self, tenant_id: UUID, rules: MatchingRules, actor: str) -> None: ...
