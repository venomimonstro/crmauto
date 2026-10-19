import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations,models
from django.db.models import Q,F

class Migration(migrations.Migration):
    initial=True
    dependencies=[("identity","0001_initial"),("workorders","0001_initial")]
    operations=[
      migrations.CreateModel(name="Warehouse",fields=[
        ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
        ("name",models.CharField(max_length=120)),("active",models.BooleanField(default=True)),
        ("branch",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.branch")),
        ("organization",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.organization"))]),
      migrations.CreateModel(name="Part",fields=[
        ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
        ("sku",models.CharField(max_length=80)),("name",models.CharField(max_length=200)),
        ("condition",models.CharField(max_length=12,default="new",choices=[("new","Новая"),("used","Б/у")])),
        ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
        ("organization",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.organization"))]),
      migrations.CreateModel(name="Stock",fields=[
        ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
        ("quantity",models.PositiveIntegerField(default=0)),("reserved",models.PositiveIntegerField(default=0)),
        ("organization",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.organization")),
        ("warehouse",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="inventory.warehouse")),
        ("part",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="inventory.part"))]),
      migrations.CreateModel(name="Reservation",fields=[
        ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
        ("quantity",models.PositiveIntegerField()),
        ("state",models.CharField(max_length=12,default="active",choices=[("active","Активен"),("released","Снят"),("issued","Выдан")])),
        ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
        ("organization",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.organization")),
        ("stock",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="inventory.stock")),
        ("order",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="workorders.workorder"))]),
      migrations.CreateModel(name="Movement",fields=[
        ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
        ("kind",models.CharField(max_length=12,choices=[("receipt","Приход"),("issue","Расход")])),
        ("quantity",models.PositiveIntegerField()),("created_at",models.DateTimeField(default=django.utils.timezone.now)),
        ("organization",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.organization")),
        ("stock",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="inventory.stock")),
        ("reservation",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,null=True,blank=True,to="inventory.reservation"))]),
      migrations.AddConstraint(model_name="warehouse",constraint=models.UniqueConstraint(fields=("branch","name"),name="inv_warehouse_unique")),
      migrations.AddConstraint(model_name="part",constraint=models.UniqueConstraint(fields=("organization","sku"),name="inv_sku_unique")),
      migrations.AddConstraint(model_name="stock",constraint=models.UniqueConstraint(fields=("warehouse","part"),name="inv_stock_unique")),
      migrations.AddConstraint(model_name="stock",constraint=models.CheckConstraint(condition=Q(quantity__gte=F("reserved")),name="inv_reserve_within_stock")),
      migrations.AddConstraint(model_name="reservation",constraint=models.CheckConstraint(condition=Q(quantity__gt=0),name="inv_res_qty_positive")),
      migrations.AddConstraint(model_name="movement",constraint=models.CheckConstraint(condition=Q(quantity__gt=0),name="inv_movement_positive")),
    ]
