"""SQL implementation of the matching settings port (SAPS-28); runs in the request's transaction."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saps.adapters.persistence.models import MatchingSettings, UserAccount
from saps.domain.matching import MatchingRules
from saps.ports.matching_settings import MatchingSettingsView


class SqlMatchingSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tenant_id: UUID) -> MatchingSettingsView:
        return await self._view(await self._session.get_one(MatchingSettings, tenant_id), tenant_id)

    async def lock(self, tenant_id: UUID) -> MatchingSettingsView:
        row = await self._session.scalar(
            select(MatchingSettings)
            .where(MatchingSettings.tenant_id == tenant_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert row is not None  # the seed creates the settings with the tenant (SAPS-27 BR-02)
        return await self._view(row, tenant_id)

    async def save(self, tenant_id: UUID, rules: MatchingRules, actor: str) -> None:
        row = await self._session.get_one(MatchingSettings, tenant_id)
        row.price_tolerance_usd = rules.price_tolerance
        row.approval_threshold_usd = rules.approval_threshold
        row.updated_by = actor
        await self._session.flush()
        await self._session.refresh(row)  # updated_at is set by the database

    async def _view(self, row: MatchingSettings, tenant_id: UUID) -> MatchingSettingsView:
        display_name = await self._session.scalar(
            select(UserAccount.display_name).where(
                UserAccount.tenant_id == tenant_id, UserAccount.username == row.updated_by
            )
        )
        return MatchingSettingsView(
            MatchingRules(row.price_tolerance_usd, row.approval_threshold_usd),
            row.updated_at,
            display_name or row.updated_by,
        )
