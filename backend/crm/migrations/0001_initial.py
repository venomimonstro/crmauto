import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.db.models import Q, F

class Migration(migrations.Migration):
    initial = True
    dependencies = [("identity", "0001_initial")]
    operations = [
        migrations.CreateModel(name="Customer", fields=[
            ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ("kind", models.CharField(choices=[("person", "Физлицо"), ("company", "Организация")], default="person", max_length=8)),
            ("name", models.CharField(max_length=200)),
            ("phone", models.CharField(blank=True, max_length=32)),
            ("phone_digits", models.CharField(blank=True, db_index=True, max_length=18)),
            ("email", models.EmailField(blank=True, max_length=254)),
            ("notes", models.TextField(blank=True)),
            ("archived_at", models.DateTimeField(blank=True, null=True)),
            ("version", models.PositiveIntegerField(default=1)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.organization")),
        ]),
        migrations.CreateModel(name="Vehicle", fields=[
            ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ("vin", models.CharField(blank=True, max_length=17)),
            ("plate", models.CharField(blank=True, max_length=20)),
            ("make", models.CharField(max_length=100)),
            ("model", models.CharField(max_length=100)),
            ("year", models.PositiveSmallIntegerField(blank=True, null=True)),
            ("version", models.PositiveIntegerField(default=1)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.organization")),
        ]),
        migrations.CreateModel(name="Ownership", fields=[
            ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ("started_on", models.DateField(default=django.utils.timezone.localdate)),
            ("ended_on", models.DateField(blank=True, null=True)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ownerships", to="crm.customer")),
            ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ownerships", to="crm.vehicle")),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.organization")),
        ]),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["organization", "name"], name="crm_customer_name_idx")),
        migrations.AddIndex(model_name="vehicle", index=models.Index(fields=["organization", "plate"], name="crm_vehicle_plate_idx")),
        migrations.AddConstraint(model_name="vehicle", constraint=models.UniqueConstraint(fields=("organization", "vin"), condition=~Q(vin=""), name="crm_unique_vin_in_tenant")),
        migrations.AddConstraint(model_name="ownership", constraint=models.UniqueConstraint(fields=("vehicle",), condition=Q(ended_on__isnull=True), name="crm_one_active_owner")),
        migrations.AddConstraint(model_name="ownership", constraint=models.CheckConstraint(condition=Q(ended_on__isnull=True) | Q(ended_on__gte=F("started_on")), name="crm_owner_valid_interval")),
    ]
