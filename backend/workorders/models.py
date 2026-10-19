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

class AdditionalWork(models.Model):
    """Supplemental scope stays unbillable until a separate signed approval flow exists."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    order=models.ForeignKey(WorkOrder,on_delete=models.PROTECT,related_name="additional_works")
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    title=models.CharField(max_length=200)
    description=models.TextField()
    amount_minor=models.PositiveBigIntegerField()
    status=models.CharField(max_length=16,choices=[
        ("proposed","Предложена"),("declined","Отклонена"),
        ("approved","Подтверждена")],default="proposed")
    approval_reference=models.CharField(max_length=250,blank=True)
    created_at=models.DateTimeField(default=timezone.now)
    decided_at=models.DateTimeField(null=True,blank=True)

class RepairTask(models.Model):
    """Single assigned mechanic task; time is recorded by server, not caller."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    order=models.ForeignKey(WorkOrder,on_delete=models.PROTECT,related_name="repair_tasks")
    mechanic=models.ForeignKey("identity.Membership",on_delete=models.PROTECT)
    title=models.CharField(max_length=200)
    state=models.CharField(max_length=12,choices=[("assigned","Назначено"),("running","В работе"),
        ("done","Выполнено"),("cancelled","Отменено")],default="assigned")
    started_at=models.DateTimeField(null=True,blank=True)
    completed_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=["mechanic"],condition=Q(state="running"),
                name="wo_one_running_task_per_mechanic"),
            models.CheckConstraint(condition=Q(completed_at__isnull=True)|Q(started_at__isnull=False),
                name="wo_task_end_requires_start"),
        ]

class OrderDocument(models.Model):
    """A versioned, immutable-by-API, printable snapshot. No forged signature state."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("identity.Organization",on_delete=models.PROTECT)
    order=models.ForeignKey(WorkOrder,related_name="documents",on_delete=models.PROTECT)
    doc_type=models.CharField(max_length=20,choices=[
        ("work_order","Заказ-наряд"),("intake","Акт приёмки"),
        ("completion","Акт работ (проект)"),("handover","Акт выдачи (проект)")])
    revision=models.PositiveIntegerField()
    html_snapshot=models.TextField()
    sha256=models.CharField(max_length=64)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["order","doc_type","revision"],name="wo_document_version_unique")]
