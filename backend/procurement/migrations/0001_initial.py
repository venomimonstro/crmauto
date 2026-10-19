import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations,models
from django.db.models import Q,F
class Migration(migrations.Migration):
    initial=True
    dependencies=[("identity","0001_initial"),("inventory","0001_initial")]
    operations=[
        migrations.CreateModel(name="Supplier",fields=[
          ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
          ("name",models.CharField(max_length=200)),("inn",models.CharField(max_length=12,blank=True)),
          ("phone",models.CharField(max_length=32,blank=True)),("active",models.BooleanField(default=True)),
          ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
          ("organization",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.organization"))]),
        migrations.CreateModel(name="PurchaseOrder",fields=[
          ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
          ("status",models.CharField(max_length=12,default="draft",choices=[("draft","Черновик"),("ordered","Заказан"),("partial","Частично принят"),("received","Принят"),("cancelled","Отменён")])),
          ("supplier_reference",models.CharField(max_length=100,blank=True)),
          ("version",models.PositiveIntegerField(default=1)),
          ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
          ("organization",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.organization")),
          ("branch",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.branch")),
          ("warehouse",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="inventory.warehouse")),
          ("supplier",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="procurement.supplier"))]),
        migrations.CreateModel(name="PurchaseLine",fields=[
          ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
          ("ordered",models.PositiveIntegerField()),("received",models.PositiveIntegerField(default=0)),
          ("unit_cost_minor",models.PositiveBigIntegerField()),
          ("purchase",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="lines",to="procurement.purchaseorder")),
          ("part",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="inventory.part"))]),
        migrations.CreateModel(name="GoodsReceipt",fields=[
          ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
          ("quantity",models.PositiveIntegerField()),("unit_cost_minor",models.PositiveBigIntegerField()),
          ("received_at",models.DateTimeField(default=django.utils.timezone.now)),
          ("organization",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.organization")),
          ("purchase",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="receipts",to="procurement.purchaseorder")),
          ("movement",models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,to="inventory.movement")),
          ("part",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="inventory.part"))]),
        migrations.AddIndex(model_name="purchaseorder",index=models.Index(fields=["organization","branch","created_at"],name="proc_po_tenant_date_idx")),
        migrations.AddConstraint(model_name="purchaseline",constraint=models.UniqueConstraint(fields=("purchase","part"),name="proc_one_part_per_po")),
        migrations.AddConstraint(model_name="purchaseline",constraint=models.CheckConstraint(condition=Q(ordered__gt=0),name="proc_order_qty_positive")),
        migrations.AddConstraint(model_name="purchaseline",constraint=models.CheckConstraint(condition=Q(received__lte=F("ordered")),name="proc_received_lte_ordered")),
        migrations.AddConstraint(model_name="goodsreceipt",constraint=models.CheckConstraint(condition=Q(quantity__gt=0),name="proc_receipt_positive")),
    ]
