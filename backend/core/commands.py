"""Atomic tenant-scoped idempotent commands; replays cannot duplicate records."""
import hashlib
import json
from uuid import UUID

from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError
from identity.models import Organization
from .models import CommandReceipt


class BusinessConflict(APIException):
    status_code = 409
    default_detail = "Конфликт состояния. Обновите данные и повторите операцию."
    default_code = "conflict"


def execute_command(request, scope, operation, callback):
    try:
        key = UUID(request.headers.get("Idempotency-Key", ""))
    except (TypeError, ValueError, AttributeError):
        raise ValidationError({"Idempotency-Key": "Обязателен UUID ключ команды."})
    payload = json.dumps(request.data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    with transaction.atomic():
        # MVP serialises commands per company. Later replace with per-aggregate locking.
        Organization.objects.select_for_update().get(pk=scope.organization_id)
        old = CommandReceipt.objects.filter(
            organization_id=scope.organization_id, operation=operation, key=key
        ).first()
        if old:
            if old.user_id != request.user.pk:
                raise BusinessConflict("Ключ команды принадлежит другому пользователю.")
            if old.request_digest != digest:
                raise BusinessConflict("Ключ команды уже использован с другим содержимым.")
            return old.response_body, old.response_status
        body, code = callback()
        CommandReceipt.objects.create(
            organization_id=scope.organization_id, operation=operation, key=key,
            request_digest=digest, response_body=body, response_status=code, user=request.user,
        )
        return body, code
