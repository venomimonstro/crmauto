import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.db.models import Q, F

class Migration(migrations.Migration):
    initial = True
    dependencies = [("identity","0001_initial"), ("crm","0001_initial")]
    operations = [
        migrations.CreateModel(name="ServiceBay", fields=[
            ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ("name", models.CharField(max_length=100)),
            ("active", models.BooleanField(default=True)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.branch")),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.organization")),
        ]),
        migrations.CreateModel(name="Appointment", fields=[
            ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ("start_at", models.DateTimeField()),
            ("end_at", models.DateTimeField()),
            ("status", models.CharField(max_length=12, default="booked", choices=[("booked","Записан"),("confirmed","Подтверждён"),("arrived","Прибыл"),("cancelled","Отменён"),("no_show","Не прибыл"),("completed","Завершён")])),
            ("description", models.CharField(blank=True, max_length=500)),
            ("version", models.PositiveIntegerField(default=1)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("bay", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, to="scheduling.servicebay")),
            ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="crm.customer")),
            ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="crm.vehicle")),
            ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.branch")),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.organization")),
        ]),
        migrations.CreateModel(name="Visit", fields=[
            ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ("arrived_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("status", models.CharField(max_length=8, default="open", choices=[("open","В работе"),("closed","Закрыт")])),
            ("appointment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="visit", to="scheduling.appointment")),
            ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.branch")),
            ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="crm.customer")),
            ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="crm.vehicle")),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.organization")),
        ]),
        migrations.AddConstraint(model_name="servicebay", constraint=models.UniqueConstraint(fields=("branch","name"), name="schedule_bay_unique_name")),
        migrations.AddConstraint(model_name="appointment", constraint=models.CheckConstraint(condition=Q(end_at__gt=F("start_at")), name="schedule_time_order")),
        migrations.AddIndex(model_name="appointment", index=models.Index(fields=["organization","branch","start_at"], name="schedule_branch_start_idx")),
    ]
