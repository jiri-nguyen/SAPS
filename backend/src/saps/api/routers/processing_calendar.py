"""Processing calendar operations: getProcessingCalendar, updateProcessingCalendar (SAPS-52, DEC-062)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from saps.api.deps import User, processing_calendar_service, require_roles
from saps.api.problems import FieldProblem
from saps.api.schemas import ProcessingCalendar, ProcessingCalendarUpdate
from saps.application.processing_calendar import InvalidCalendarError, ProcessingCalendarService
from saps.domain.users import CurrentUser, Role

router = APIRouter(prefix="/v1/processing-calendar", tags=["ProcessingCalendar"])

Manager = Annotated[CurrentUser, Depends(require_roles(Role.ACCOUNTING_MANAGER))]
Service = Annotated[ProcessingCalendarService, Depends(processing_calendar_service)]


@router.get("", operation_id="getProcessingCalendar", response_model_by_alias=True)
async def get_processing_calendar(user: User, service: Service) -> ProcessingCalendar:
    """Both roles: every user of the company sees the banner of a closed period (BR-08)."""
    return ProcessingCalendar.from_status(await service.get(user))


@router.put("", operation_id="updateProcessingCalendar", response_model_by_alias=True)
async def update_processing_calendar(
    body: ProcessingCalendarUpdate, user: Manager, service: Service
) -> ProcessingCalendar:
    try:
        calendar = await service.replace(user, [rule.rule() for rule in body.rules])
    except InvalidCalendarError as exc:
        errors = [{"field": field, "message": message} for field, message in exc.fields.items()]
        raise FieldProblem(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.detail, errors) from exc
    return ProcessingCalendar.from_status(calendar)
