import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [("identity", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="CommandReceipt", fields=[
            ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ("operation", models.CharField(max_length=100)),
            ("key", models.UUIDField()),
            ("request_digest", models.CharField(max_length=64)),
            ("response_body", models.JSONField()),
            ("response_status", models.PositiveSmallIntegerField()),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="identity.organization")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="commandreceipt",
            constraint=models.UniqueConstraint(fields=("organization", "operation", "key"), name="crm_unique_command_key")),
    ]
