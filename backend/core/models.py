"""Idempotent HTTP command receipt for non-GET operations."""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class CommandReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT)
    operation = models.CharField(max_length=100)
    key = models.UUIDField()
    request_digest = models.CharField(max_length=64)
    response_body = models.JSONField()
    response_status = models.PositiveSmallIntegerField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "operation", "key"],
                                                name="crm_unique_command_key")]
