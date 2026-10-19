import uuid
from django.db import models
from django.db.models import Q,F
from django.utils import timezone

class Supplier(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("identity.Organization",on_delete=models.PROTECT)
    name=models.CharField(max_length=200)
    inn=models.CharField(max_length=12,blank=True)
    phone=models.CharField(max_length=32,blank=True)
    active=models.BooleanField(default=True)
    created_at=models.DateTimeField(default=timezone.now)

class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT="draft","Черновик"
        ORDERED="ordered","Заказан"
        PARTIAL="partial","Частично принят"
        RECEIVED="received","Принят"
        CANCELLED="cancelled","Отменён"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("identity.Organization",on_delete=models.PROTECT)
    branch=models.ForeignKey("identity.Branch",on_delete=models.PROTECT)
    warehouse=models.ForeignKey("inventory.Warehouse",on_delete=models.PROTECT)
    supplier=models.ForeignKey(Supplier,on_delete=models.PROTECT)
    status=models.CharField(max_length=12,choices=Status.choices,default=Status.DRAFT)
    supplier_reference=models.CharField(max_length=100,blank=True)
    version=models.PositiveIntegerField(default=1)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        indexes=[models.Index(fields=["organization","branch","created_at"],name="proc_po_tenant_date_idx")]

class PurchaseLine(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    purchase=models.ForeignKey(PurchaseOrder,related_name="lines",on_delete=models.PROTECT)
    part=models.ForeignKey("inventory.Part",on_delete=models.PROTECT)
    ordered=models.PositiveIntegerField()
    received=models.PositiveIntegerField(default=0)
    unit_cost_minor=models.PositiveBigIntegerField()
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=["purchase","part"],name="proc_one_part_per_po"),
            models.CheckConstraint(condition=Q(ordered__gt=0),name="proc_order_qty_positive"),
            models.CheckConstraint(condition=Q(received__lte=F("ordered")),name="proc_received_lte_ordered"),
        ]

class GoodsReceipt(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("identity.Organization",on_delete=models.PROTECT)
    purchase=models.ForeignKey(PurchaseOrder,related_name="receipts",on_delete=models.PROTECT)
    movement=models.OneToOneField("inventory.Movement",on_delete=models.PROTECT)
    part=models.ForeignKey("inventory.Part",on_delete=models.PROTECT)
    quantity=models.PositiveIntegerField()
    unit_cost_minor=models.PositiveBigIntegerField()
    received_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name="proc_receipt_positive")]
