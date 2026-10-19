import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.utils import timezone

class ServiceBay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT)
    branch = models.ForeignKey("identity.Branch", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["branch", "name"], name="schedule_bay_unique_name")]

    def clean(self):
        if self.branch_id and self.organization_id and self.branch.organization_id != self.organization_id:
            raise ValidationError("Пост должен принадлежать организации филиала.")

class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Записан"
        CONFIRMED = "confirmed", "Подтверждён"
        ARRIVED = "arrived", "Прибыл"
        CANCELLED = "cancelled", "Отменён"
        NO_SHOW = "no_show", "Не прибыл"
        COMPLETED = "completed", "Завершён"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT)
    branch = models.ForeignKey("identity.Branch", on_delete=models.PROTECT)
    customer = models.ForeignKey("crm.Customer", on_delete=models.PROTECT)
    vehicle = models.ForeignKey("crm.Vehicle", on_delete=models.PROTECT)
    bay = models.ForeignKey(ServiceBay, on_delete=models.PROTECT, null=True, blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.BOOKED)
    description = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(end_at__gt=F("start_at")), name="schedule_time_order")]
        indexes = [models.Index(fields=["organization", "branch", "start_at"], name="schedule_branch_start_idx")]

    def clean(self):
        if self.branch_id and self.organization_id and self.branch.organization_id != self.organization_id:
            raise ValidationError("Чужой филиал.")
        if self.customer_id and self.organization_id and self.customer.organization_id != self.organization_id:
            raise ValidationError("Чужой клиент.")
        if self.vehicle_id and self.organization_id and self.vehicle.organization_id != self.organization_id:
            raise ValidationError("Чужой автомобиль.")
        if self.bay_id and (self.bay.branch_id != self.branch_id or self.bay.organization_id != self.organization_id):
            raise ValidationError("Чужой рабочий пост.")

class Visit(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "В работе"
        CLOSED = "closed", "Закрыт"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT)
    branch = models.ForeignKey("identity.Branch", on_delete=models.PROTECT)
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT, related_name="visit")
    customer = models.ForeignKey("crm.Customer", on_delete=models.PROTECT)
    vehicle = models.ForeignKey("crm.Vehicle", on_delete=models.PROTECT)
    arrived_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.OPEN)
