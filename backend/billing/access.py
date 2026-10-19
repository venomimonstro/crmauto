"""Central server-side SaaS write policy; never trust frontend subscription state."""
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from .models import Subscription


def may_write(organization_id, *, at=None):
    subscription = Subscription.objects.select_related("plan").filter(
        organization_id=organization_id,
        organization__is_active=True,
        plan__active=True,
    ).first()
    if subscription is None:
        return False
    now = at or timezone.now()
    if subscription.state == "active":
        return subscription.paid_through is not None and subscription.paid_through > now
    if subscription.state == "trial":
        return subscription.trial_ends_at is not None and subscription.trial_ends_at > now
    return False


def enforce_write_access(request, organization_id):
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if not settings.BILLING_ENFORCE_WRITES:
        return
    if not may_write(organization_id):
        raise PermissionDenied("Подписка неактивна. Доступно только чтение данных. Проверьте тариф.")
