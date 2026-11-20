"""Matching settings operations: getMatchingSettings, updateMatchingSettings (SAPS-28)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from saps.api.deps import matching_settings_service, require_roles
from saps.api.problems import FieldProblem
from saps.api.schemas import MatchingSettings, MatchingSettingsUpdate
from saps.application.matching_settings import InvalidSettingsError, MatchingSettingsService
from saps.domain.users import CurrentUser, Role

router = APIRouter(prefix="/v1/matching-settings", tags=["MatchingSettings"])
log = logging.getLogger("saps.api.matching_settings")

Manager = Annotated[CurrentUser, Depends(require_roles(Role.ACCOUNTING_MANAGER))]
Service = Annotated[MatchingSettingsService, Depends(matching_settings_service)]


@router.get("", operation_id="getMatchingSettings", response_model_by_alias=True)
async def get_matching_settings(user: Manager, service: Service) -> MatchingSettings:
    return MatchingSettings.from_view(await service.get(user))


@router.put("", operation_id="updateMatchingSettings", response_model_by_alias=True)
async def update_matching_settings(
    body: MatchingSettingsUpdate, user: Manager, service: Service
) -> MatchingSettings:
    try:
        change = await service.update(user, body.rules())
    except InvalidSettingsError as exc:
        errors = [{"field": field, "message": message} for field, message in exc.fields.items()]
        raise FieldProblem(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.detail, errors) from exc
    if change.previous is not None:  # nothing is logged when the values did not change (EC-05)
        log.info(
            "matching_settings_updated",
            extra={
                "tenant_id": str(user.tenant_id),
                "user_id": str(user.user_id),
                "old_price_tolerance": str(change.previous.price_tolerance),
                "old_approval_threshold": str(change.previous.approval_threshold),
                "new_price_tolerance": str(change.current.rules.price_tolerance),
                "new_approval_threshold": str(change.current.rules.approval_threshold),
            },
        )
    return MatchingSettings.from_view(change.current)
