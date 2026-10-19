import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations,models
from django.db.models import Q

class Migration(migrations.Migration):
    initial=True
    dependencies=[("identity","0001_initial"),("crm","0001_initial"),("scheduling","0001_initial"),
                  migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(name="WorkOrder",fields=[
            ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
            ("status",models.CharField(max_length=16,default="draft",choices=[("draft","Черновик"),("awaiting","Ожидает согласования"),("approved","Согласован"),("in_progress","В работе"),("qa","Проверка"),("ready","Готов к выдаче"),("delivered","Выдан"),("cancelled","Отменён")])),
            ("complaint",models.TextField(blank=True)),
            ("odometer_km",models.PositiveIntegerField(blank=True,null=True)),
            ("existing_damage",models.TextField(blank=True)),
            ("received_at",models.DateTimeField(default=django.utils.timezone.now)),
            ("version",models.PositiveIntegerField(default=1)),
            ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
            ("branch",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.branch")),
            ("organization",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="identity.organization")),
            ("customer",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="crm.customer")),
            ("vehicle",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="crm.vehicle")),
            ("visit",models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name="workorder",to="scheduling.visit")),
            ("created_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="Estimate",fields=[
            ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
            ("revision",models.PositiveIntegerField()),
            ("state",models.CharField(max_length=12,default="draft",choices=[("draft","Черновик"),("submitted","Отправлена"),("approved","Согласована"),("rejected","Отклонена"),("superseded","Заменена")])),
            ("total_minor",models.BigIntegerField(default=0)),
            ("currency",models.CharField(default="RUB",max_length=3)),
            ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
            ("approved_at",models.DateTimeField(blank=True,null=True)),
            ("approval_method",models.CharField(blank=True,max_length=32)),
            ("approval_reference",models.CharField(blank=True,max_length=250)),
            ("order",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="estimates",to="workorders.workorder")),
        ]),
        migrations.CreateModel(name="EstimateLine",fields=[
            ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
            ("kind",models.CharField(max_length=12,choices=[("labor","Работа"),("material","Материал (план)"),("external","Подрядчик")])),
            ("title",models.CharField(max_length=200)),
            ("quantity",models.DecimalField(decimal_places=3,max_digits=12)),
            ("unit_price_minor",models.BigIntegerField()),
            ("total_minor",models.BigIntegerField()),
            ("estimate",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="lines",to="workorders.estimate")),
        ]),
        migrations.CreateModel(name="OrderTransition",fields=[
            ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
            ("previous",models.CharField(max_length=16)),
            ("current",models.CharField(max_length=16)),
            ("occurred_at",models.DateTimeField(default=django.utils.timezone.now)),
            ("reason",models.CharField(blank=True,max_length=500)),
            ("actor",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL)),
            ("order",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="transitions",to="workorders.workorder")),
        ]),
        migrations.AddConstraint(model_name="estimate",constraint=models.UniqueConstraint(fields=("order","revision"),name="wo_revision_unique")),
        migrations.AddConstraint(model_name="estimate",constraint=models.UniqueConstraint(fields=("order",),condition=Q(state="draft"),name="wo_one_draft_estimate")),
        migrations.AddConstraint(model_name="estimate",constraint=models.CheckConstraint(condition=Q(total_minor__gte=0),name="wo_total_nonnegative")),
        migrations.AddConstraint(model_name="estimateline",constraint=models.CheckConstraint(condition=Q(quantity__gt=0),name="wo_line_quantity_positive")),
        migrations.AddConstraint(model_name="estimateline",constraint=models.CheckConstraint(condition=Q(unit_price_minor__gte=0),name="wo_line_price_nonnegative")),
        migrations.AddConstraint(model_name="estimateline",constraint=models.CheckConstraint(condition=Q(total_minor__gte=0),name="wo_line_total_nonnegative")),
    ]
