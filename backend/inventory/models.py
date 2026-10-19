import uuid
from django.db import models
from django.db.models import Q,F
from django.utils import timezone

class Warehouse(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("identity.Organization",on_delete=models.PROTECT)
    branch=models.ForeignKey("identity.Branch",on_delete=models.PROTECT)
    name=models.CharField(max_length=120)
    active=models.BooleanField(default=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["branch","name"],name="inv_warehouse_unique")]

class Part(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("identity.Organization",on_delete=models.PROTECT)
    sku=models.CharField(max_length=80)
    name=models.CharField(max_length=200)
    condition=models.CharField(max_length=12,choices=[("new","Новая"),("used","Б/у")],default="new")
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["organization","sku"],name="inv_sku_unique")]

class Stock(models.Model):
    """Row lock serializes every reserve/receive/issue for same part and warehouse."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("identity.Organization",on_delete=models.PROTECT)
    warehouse=models.ForeignKey(Warehouse,on_delete=models.PROTECT)
    part=models.ForeignKey(Part,on_delete=models.PROTECT)
    quantity=models.PositiveIntegerField(default=0)
    reserved=models.PositiveIntegerField(default=0)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=["warehouse","part"],name="inv_stock_unique"),
            models.CheckConstraint(condition=Q(quantity__gte=F("reserved")),name="inv_reserve_within_stock"),
        ]

class Reservation(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("identity.Organization",on_delete=models.PROTECT)
    stock=models.ForeignKey(Stock,on_delete=models.PROTECT)
    order=models.ForeignKey("workorders.WorkOrder",on_delete=models.PROTECT)
    quantity=models.PositiveIntegerField()
    state=models.CharField(max_length=12,default="active",choices=[("active","Активен"),("released","Снят"),("issued","Выдан")])
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name="inv_res_qty_positive")]

class Movement(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("identity.Organization",on_delete=models.PROTECT)
    stock=models.ForeignKey(Stock,on_delete=models.PROTECT)
    reservation=models.ForeignKey(Reservation,null=True,blank=True,on_delete=models.PROTECT)
    kind=models.CharField(max_length=12,choices=[("receipt","Приход"),("issue","Расход")])
    quantity=models.PositiveIntegerField()
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name="inv_movement_positive")]
