import uuid
from django.db import models
from django.db.models import Q,F
from django.utils import timezone

class Shift(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('identity.Organization',on_delete=models.PROTECT)
    branch=models.ForeignKey('identity.Branch',on_delete=models.PROTECT)
    membership=models.ForeignKey('identity.Membership',on_delete=models.PROTECT)
    begins=models.DateTimeField()
    ends=models.DateTimeField()
    state=models.CharField(max_length=12,choices=[('planned','Плановая'),('completed','Завершена'),('cancelled','Отменена')],default='planned')
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(ends__gt=F('begins')),name='workforce_shift_time_valid')]

class TireSet(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('identity.Organization',on_delete=models.PROTECT)
    branch=models.ForeignKey('identity.Branch',on_delete=models.PROTECT)
    customer=models.ForeignKey('crm.Customer',on_delete=models.PROTECT)
    vehicle=models.ForeignKey('crm.Vehicle',on_delete=models.PROTECT,null=True,blank=True)
    code=models.CharField(max_length=80)
    pieces=models.PositiveSmallIntegerField()
    description=models.CharField(max_length=300)
    storage_location=models.CharField(max_length=120)
    received_at=models.DateTimeField(default=timezone.now)
    released_at=models.DateTimeField(null=True,blank=True)
    state=models.CharField(max_length=12,choices=[('stored','Хранится'),('released','Выдан')],default='stored')
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['organization','code'],name='workforce_tireset_code'),
            models.CheckConstraint(condition=Q(pieces__gte=1,pieces__lte=16),name='workforce_tireset_pieces')
        ]
