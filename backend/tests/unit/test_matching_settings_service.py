"""SAPS-28 matching settings: value rules (BR-03) and the use case with an in-memory port."""

from datetime import timedelta
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest

from saps.application.matching_settings import InvalidSettingsError, MatchingSettingsService
from saps.domain.matching import MatchingRules, settings_errors
from saps.domain.users import CurrentUser, Role
from saps.ports.matching_settings import MatchingSettingsView
from tests.fakes import NOW

MANAGER = CurrentUser(uuid4(), uuid4(), "manager1", "Manager One", Role.ACCOUNTING_MANAGER)


class MemorySettings:
    def __init__(self) -> None:
        self.view = MatchingSettingsView(MatchingRules(D("0.5"), D("300")), NOW, "system")
        self.locked = 0
        self.saved: list[tuple[UUID, MatchingRules, str]] = []

    async def get(self, tenant_id: UUID) -> MatchingSettingsView:
        return self.view

    async def lock(self, tenant_id: UUID) -> MatchingSettingsView:
        self.locked += 1
        return self.view

    async def save(self, tenant_id: UUID, rules: MatchingRules, actor: str) -> None:
        self.saved.append((tenant_id, rules, actor))
        self.view = MatchingSettingsView(rules, NOW + timedelta(minutes=1), "Manager One")


@pytest.mark.parametrize(
    ("tolerance", "threshold"), [("0", "0"), ("0.0001", "0.01"), ("1000000", "99999999")]
)
def test_zero_and_large_values_are_allowed(tolerance: str, threshold: str) -> None:  # DEC-045
    assert settings_errors(MatchingRules(D(tolerance), D(threshold))) == {}


def test_negative_values_name_the_field() -> None:  # EC-03
    assert set(settings_errors(MatchingRules(D("-0.01"), D("300")))) == {"priceToleranceUsd"}
    assert set(settings_errors(MatchingRules(D("0.5"), D("-1")))) == {"approvalThresholdUsd"}
    assert set(settings_errors(MatchingRules(D("-1"), D("-1")))) == {
        "priceToleranceUsd",
        "approvalThresholdUsd",
    }
    assert settings_errors(MatchingRules(D("-0"), D("-0.00"))) == {}  # minus zero is zero


async def test_get_reads_the_tenant_settings() -> None:
    repo = MemorySettings()
    assert await MatchingSettingsService(repo).get(MANAGER) == repo.view


async def test_update_saves_both_values_as_the_user() -> None:
    repo = MemorySettings()
    change = await MatchingSettingsService(repo).update(MANAGER, MatchingRules(D("1.00"), D("500")))
    assert repo.saved == [(MANAGER.tenant_id, MatchingRules(D("1.00"), D("500")), "manager1")]
    assert change.previous == MatchingRules(D("0.5"), D("300"))
    assert (change.current.rules, change.current.updated_by) == (
        MatchingRules(D("1.00"), D("500")),
        "Manager One",
    )


async def test_the_same_values_change_nothing() -> None:  # EC-05
    repo = MemorySettings()
    change = await MatchingSettingsService(repo).update(MANAGER, MatchingRules(D("0.50"), D("300.00")))
    assert repo.saved == [] and change.previous is None
    assert change.current.updated_by == "system"


async def test_invalid_values_are_refused_before_the_lock() -> None:  # BR-03, EC-03
    repo = MemorySettings()
    with pytest.raises(InvalidSettingsError) as caught:
        await MatchingSettingsService(repo).update(MANAGER, MatchingRules(D("-1"), D("300")))
    assert set(caught.value.fields) == {"priceToleranceUsd"}
    assert repo.locked == 0 and repo.saved == []
