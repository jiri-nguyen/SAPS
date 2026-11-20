"""Integration: SAPS-28 matching settings through the API on a real PostgreSQL (TS-01 … TS-06)."""

import asyncio
from decimal import Decimal as D
from typing import Any

import pytest

from tests.integration.api_world import Api

pytestmark = pytest.mark.integration

PATH = "/v1/matching-settings"
DS01 = "ds-01/invoices/ds-01-trade-po.pdf"  # matched
DS03 = "ds-03/invoices/ds-03-above-threshold.pdf"  # 495.00 → Pending approval
DS12 = "ds-12/invoices/ds-12-price-outside-tolerance.pdf"  # EX6
DS18 = "ds-18/invoices/ds-18-settings-tolerance.pdf"  # 50.80 vs 50.00: EX6 at 0.5, matches at 1.00


async def _put(api: Api, who: str, tolerance: Any, threshold: Any) -> Any:
    return await api.request(
        who, "PUT", PATH, json={"priceToleranceUsd": tolerance, "approvalThresholdUsd": threshold}
    )


async def _read(api: Api) -> dict[str, Any]:
    response = await api.request("manager", "GET", PATH)
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


# TS-01 / BR-02, BR-05 --------------------------------------------------------------------------------


async def test_defaults_then_a_save_shows_who_changed_it(api: Api) -> None:
    before = await _read(api)
    assert (D(before["priceToleranceUsd"]), D(before["approvalThresholdUsd"])) == (D("0.5"), D("300"))
    assert before["updatedBy"] == "system"

    response = await _put(api, "manager", "1.00", "450.50")
    assert response.status_code == 200
    saved = response.json()
    assert (D(saved["priceToleranceUsd"]), D(saved["approvalThresholdUsd"])) == (D("1"), D("450.50"))
    assert saved["updatedBy"] == "Manager"  # the display name, not the username

    after = await _read(api)
    assert after == saved and after["updatedAt"] > before["updatedAt"]


async def test_another_manager_overwrites_the_last_change(api: Api) -> None:  # EC-04, DEC-046
    await _put(api, "manager", "1", "400")
    await _put(api, "manager2", "2", "500")
    body = await _read(api)
    assert (D(body["priceToleranceUsd"]), D(body["approvalThresholdUsd"]), body["updatedBy"]) == (
        D("2"),
        D("500"),
        "Second Manager",
    )


async def test_two_managers_saving_at_once_leave_one_complete_set(api: Api) -> None:  # EC-04
    first, second = await asyncio.gather(_put(api, "manager", "1", "400"), _put(api, "manager2", "2", "500"))
    assert (first.status_code, second.status_code) == (200, 200)
    body = await _read(api)
    assert (D(body["priceToleranceUsd"]), D(body["approvalThresholdUsd"])) in {
        (D("1"), D("400")),
        (D("2"), D("500")),
    }


# TS-02 / BR-01, EC-01 --------------------------------------------------------------------------------


async def test_members_are_refused(api: Api) -> None:
    assert (await api.request("alice", "GET", PATH)).status_code == 403
    assert (await _put(api, "alice", "1", "400")).status_code == 403
    assert D((await _read(api))["priceToleranceUsd"]) == D("0.5")


# TS-03 / BR-03, EC-02, EC-03 -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tolerance", "threshold"),
    [
        (None, "300"),  # missing
        ("0.5", None),
        ("abc", "300"),  # not a number
        ("0.5", "1e3"),
        ("0.12345", "300"),  # more than 4 decimals
        ("0.5", "300.123"),  # more than 2 decimals
        (0.5, "300"),  # a JSON number, not a string
        ("", "300"),
    ],
)
async def test_malformed_values_are_a_bad_request(api: Api, tolerance: Any, threshold: Any) -> None:
    body = {"priceToleranceUsd": tolerance, "approvalThresholdUsd": threshold}
    body = {key: value for key, value in body.items() if value is not None}
    response = await api.request("manager", "PUT", PATH, json=body)
    assert response.status_code == 400 and response.headers["content-type"].startswith(
        "application/problem+json"
    )
    assert D((await _read(api))["priceToleranceUsd"]) == D("0.5")


@pytest.mark.parametrize(
    ("tolerance", "threshold", "field"),
    [("-0.01", "300", "priceToleranceUsd"), ("0.5", "-1", "approvalThresholdUsd")],
)
async def test_negative_values_are_unprocessable_and_name_the_field(
    api: Api, tolerance: str, threshold: str, field: str
) -> None:
    response = await _put(api, "manager", tolerance, threshold)
    assert response.status_code == 422
    assert [e["field"] for e in response.json()["errors"]] == [field]
    assert D((await _read(api))["approvalThresholdUsd"]) == D("300")


async def test_zero_is_allowed(api: Api) -> None:  # DEC-045
    response = await _put(api, "manager", "0", "0")
    assert response.status_code == 200
    body = response.json()
    assert (D(body["priceToleranceUsd"]), D(body["approvalThresholdUsd"])) == (D(0), D(0))


# TS-04 / EC-05 ---------------------------------------------------------------------------------------


async def test_the_same_values_change_nothing(api: Api) -> None:
    await _put(api, "manager", "1.00", "450")
    saved = await _read(api)
    again = await _put(api, "manager2", "1", "450.00")  # same numbers, written differently, by someone else
    assert again.status_code == 200 and again.json() == saved
    assert await _read(api) == saved  # updatedBy and updatedAt stay


# TS-05 / BR-04, EC-06 --------------------------------------------------------------------------------


async def test_ds18_matches_after_the_tolerance_is_raised(api: Api) -> None:
    processed_before = await api.sample(DS01)
    stuck = await api.sample(DS12)
    assert (await api.get(stuck))["status"] == "EXCEPTION"

    assert (await _put(api, "manager", "1.00", "300")).status_code == 200

    ds18 = await api.sample(DS18)
    body = await api.get(ds18)
    assert body["status"] == "PENDING_REVIEW" and body["exceptions"] == []
    assert D(body["priceToleranceApplied"]) == D("1")
    assert D((await api.get(processed_before))["priceToleranceApplied"]) == D("0.5")  # keeps its own value
    stuck_after = await api.get(stuck)
    assert stuck_after["status"] == "EXCEPTION"  # no automatic re-matching (EC-06)
    assert D(stuck_after["priceToleranceApplied"]) == D("0.5")


# TS-06 / BR-04 ---------------------------------------------------------------------------------------


async def test_a_higher_threshold_does_not_move_an_invoice_already_waiting(api: Api) -> None:
    waiting = await api.sample(DS03)
    assert (await api.get(waiting))["status"] == "PENDING_APPROVAL"
    assert (await _put(api, "manager", "0.5", "1000")).status_code == 200
    body = await api.get(waiting)
    assert body["status"] == "PENDING_APPROVAL" and D(body["approvalThresholdApplied"]) == D("300")
    assert (await api.decide("manager", waiting, "APPROVED")).json()["status"] == "PENDING_REVIEW"
