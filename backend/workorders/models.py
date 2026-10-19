"""S05: immutable approved estimate revisions; repair != booking != payment."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q, F
from django.utils import timezone

class WorkOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        AWAITING = "awaiting", "Ожидает согласования"
        APPROVED = "approved", "Согласован"
        IN_PROGRESS = "in_progress", "В работе"
        QA = "qa", "Проверка"
        READY = "ready", "Готов к выдаче"
        DELIVERED = "delivered", "Выдан"
        CANCELLED = "cancelled", "Отменён"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT)
    branch = models.ForeignKey("identity.Branch", on_delete=models.PROTECT)
    visit = models.OneToOneField("scheduling.Visit", on_delete=models.PROTECT, related_name="workorder")
    customer = models.ForeignKey("crm.Customer", on_delete=models.PROTECT)
    vehicle = models.ForeignKey("crm.Vehicle", on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    complaint = models.TextField(blank=True)
    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    existing_damage = models.TextField(blank=True)
    received_at = models.DateTimeField(default=timezone.now)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)

class Estimate(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SUBMITTED = "submitted", "Отправлена"
        APPROVED = "approved", "Согласована"
        REJECTED = "rejected", "Отклонена"
        SUPERSEDED = "superseded", "Заменена"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(WorkOrder, related_name="estimates", on_delete=models.PROTECT)
    revision = models.PositiveIntegerField()
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    total_minor = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="RUB")
    created_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_method = models.CharField(max_length=32, blank=True)
    approval_reference = models.CharField(max_length=250, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order","revision"], name="wo_revision_unique"),
            models.UniqueConstraint(fields=["order"],condition=Q(state="draft"),name="wo_one_draft_estimate"),
            models.CheckConstraint(condition=Q(total_minor__gte=0),name="wo_total_nonnegative"),
        ]

class EstimateLine(models.Model):
    class Kind(models.TextChoices):
        LABOR = "labor", "Работа"
        MATERIAL = "material", "Материал (план)"
        EXTERNAL = "external", "Подрядчик"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estimate = models.ForeignKey(Estimate,related_name="lines",on_delete=models.PROTECT)
    kind = models.CharField(max_length=12,choices=Kind.choices)
    title = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=12,decimal_places=3)
    unit_price_minor = models.BigIntegerField()
    total_minor = models.BigIntegerField()
    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0),name="wo_line_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price_minor__gte=0),name="wo_line_price_nonnegative"),
            models.CheckConstraint(condition=Q(total_minor__gte=0),name="wo_line_total_nonnegative"),
        ]

class OrderTransition(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    order = models.ForeignKey(WorkOrder,related_name="transitions",on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    previous = models.CharField(max_length=16)
    current = models.CharField(max_length=16)
    occurred_at = models.DateTimeField(default=timezone.now)
    reason = models.CharField(max_length=500,blank=True)
