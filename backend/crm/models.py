"""Customer and vehicle records belong to one company, independent of its branches."""
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.utils import timezone


class Customer(models.Model):
    class Kind(models.TextChoices):
        PERSON = "person", "Физлицо"
        COMPANY = "company", "Организация"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.PERSON)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=32, blank=True)
    phone_digits = models.CharField(max_length=18, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "name"], name="crm_customer_name_idx")]


class Vehicle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT)
    vin = models.CharField(max_length=17, blank=True)
    plate = models.CharField(max_length=20, blank=True)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "vin"],
                      condition=~Q(vin=""), name="crm_unique_vin_in_tenant")]
        indexes = [models.Index(fields=["organization", "plate"], name="crm_vehicle_plate_idx")]


class Ownership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="ownerships")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="ownerships")
    started_on = models.DateField(default=timezone.localdate)
    ended_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["vehicle"], condition=Q(ended_on__isnull=True),
                                    name="crm_one_active_owner"),
            models.CheckConstraint(condition=Q(ended_on__isnull=True) | Q(ended_on__gte=F("started_on")),
                                   name="crm_owner_valid_interval"),
        ]

    def clean(self):
        if self.organization_id and self.vehicle_id and self.customer_id:
            if self.vehicle.organization_id != self.organization_id or self.customer.organization_id != self.organization_id:
                raise ValidationError("Клиент и автомобиль должны принадлежать одной организации.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
