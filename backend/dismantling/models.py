import uuid
from django.db import models
from django.db.models import Q
from django.utils import timezone

class Donor(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('identity.Organization',on_delete=models.PROTECT)
    branch=models.ForeignKey('identity.Branch',on_delete=models.PROTECT)
    vin=models.CharField(max_length=17,blank=True)
    description=models.CharField(max_length=250)
    acquisition_cost_minor=models.PositiveBigIntegerField()
    extra_cost_minor=models.PositiveBigIntegerField(default=0)
    created_at=models.DateTimeField(default=timezone.now)

class StorageBin(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('identity.Organization',on_delete=models.PROTECT)
    warehouse=models.ForeignKey('inventory.Warehouse',on_delete=models.PROTECT)
    code=models.CharField(max_length=64)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['warehouse','code'],name='dismantling_bin_unique')]

class SalvagedPart(models.Model):
    class State(models.TextChoices):
        RECORDED='recorded','Демонтирована'
        AVAILABLE='available','Готова к продаже'
        RESERVED='reserved','Зарезервирована'
        RETIRED='retired','Списана'
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('identity.Organization',on_delete=models.PROTECT)
    donor=models.ForeignKey(Donor,related_name='parts',on_delete=models.PROTECT)
    bin=models.ForeignKey(StorageBin,on_delete=models.PROTECT)
    inventory_code=models.CharField(max_length=80)
    name=models.CharField(max_length=200)
    condition_notes=models.CharField(max_length=500,blank=True)
    allocated_cost_minor=models.PositiveBigIntegerField(default=0)
    target_price_minor=models.PositiveBigIntegerField(default=0)
    state=models.CharField(max_length=12,choices=State.choices,default=State.RECORDED)
    reserved_order=models.ForeignKey('workorders.WorkOrder',on_delete=models.PROTECT,null=True,blank=True)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['organization','inventory_code'],name='dismantling_unique_part_code'),
            models.CheckConstraint(condition=Q(state='reserved',reserved_order__isnull=False) | ~Q(state='reserved'),name='dismantling_reservation_link'),
        ]
