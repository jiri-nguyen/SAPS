"""Matching settings (SAPS-28): the Accounting Manager reads and changes the tolerance and the threshold.

Check order for a change: 422 (values, BR-03) → lock the row → same values change nothing (EC-05) → save.
The last save wins (EC-04); there is no history, only the last change (DEC-046).
"""

from dataclasses import dataclass

from saps.application.exception_handling import UnprocessableError
from saps.domain.matching import MatchingRules, settings_errors
from saps.domain.users import CurrentUser
from saps.ports.matching_settings import MatchingSettingsRepository, MatchingSettingsView


class InvalidSettingsError(UnprocessableError):
    """Values outside the allowed range; `fields` maps the API field name to the message."""

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("The matching settings are not valid.")
        self.fields = fields


@dataclass(frozen=True)
class SettingsChange:
    """Result of a save: the settings now in force and what they replaced (None when nothing changed)."""

    current: MatchingSettingsView
    previous: MatchingRules | None


class MatchingSettingsService:
    def __init__(self, repository: MatchingSettingsRepository) -> None:
        self._repo = repository

    async def get(self, user: CurrentUser) -> MatchingSettingsView:
        return await self._repo.get(user.tenant_id)

    async def update(self, user: CurrentUser, rules: MatchingRules) -> SettingsChange:
        errors = settings_errors(rules)
        if errors:
            raise InvalidSettingsError(errors)
        before = await self._repo.lock(user.tenant_id)
        if before.rules == rules:  # EC-05: updated_by and updated_at keep showing the real last change
            return SettingsChange(before, None)
        await self._repo.save(user.tenant_id, rules, user.username)
        return SettingsChange(await self._repo.get(user.tenant_id), before.rules)
