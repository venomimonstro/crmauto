import uuid
from django.db import models
from django.utils import timezone

class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    price_minor = models.PositiveBigIntegerField()
    max_branches = models.PositiveSmallIntegerField(default=1)
    max_staff = models.PositiveSmallIntegerField(default=5)
    active = models.BooleanField(default=True)

class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField('identity.Organization', on_delete=models.PROTECT)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    state = models.CharField(max_length=12, default='trial')
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    paid_through = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)
