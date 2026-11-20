"""Notification operations: listNotifications, markNotificationRead, markAllNotificationsRead (SAPS-24)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from saps.api.deps import notification_service, require_roles
from saps.api.schemas import NotificationPage
from saps.application.notifications import NotificationInboxService, NotificationNotFoundError
from saps.domain.users import CurrentUser, Role
from saps.ports.invoices import InvalidPageTokenError

router = APIRouter(prefix="/v1/notifications", tags=["Notifications"])

Caller = Annotated[CurrentUser, Depends(require_roles(Role.ACCOUNTING_MEMBER, Role.ACCOUNTING_MANAGER))]
Service = Annotated[NotificationInboxService, Depends(notification_service)]


@router.get("", operation_id="listNotifications", response_model_by_alias=True)
async def list_notifications(
    user: Caller,
    service: Service,
    unread_only: Annotated[bool, Query(alias="unreadOnly")] = False,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    page_token: Annotated[str | None, Query(alias="pageToken")] = None,
) -> NotificationPage:
    try:
        page = await service.list(user, unread_only, page_size, page_token)
    except InvalidPageTokenError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The page token is not valid.") from exc
    return NotificationPage.from_view(page)


# Registered before `/{notification_id}/read`, which has another number of path segments.
@router.post("/read-all", operation_id="markAllNotificationsRead", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(user: Caller, service: Service) -> Response:
    await service.mark_all_read(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{notification_id}/read", operation_id="markNotificationRead", status_code=status.HTTP_204_NO_CONTENT
)
async def mark_notification_read(notification_id: UUID, user: Caller, service: Service) -> Response:
    try:
        await service.mark_read(user, notification_id)
    except NotificationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found.") from exc  # EC-02
    return Response(status_code=status.HTTP_204_NO_CONTENT)
