import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="StaffInvitation",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("email", models.EmailField(max_length=254)),
                ("role", models.CharField(max_length=16, choices=[
                    ("owner", "Владелец"), ("manager", "Управляющий"),
                    ("adviser", "Мастер-приёмщик"), ("mechanic", "Механик"),
                    ("stock", "Кладовщик"), ("cashier", "Кассир"),
                    ("viewer", "Наблюдатель"),
                ])),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(null=True, blank=True)),
                ("revoked_at", models.DateTimeField(null=True, blank=True)),
                ("branch", models.ForeignKey(to="identity.branch", null=True, blank=True,
                                             on_delete=django.db.models.deletion.PROTECT)),
                ("organization", models.ForeignKey(to="identity.organization",
                                                   related_name="staff_invitations",
                                                   on_delete=django.db.models.deletion.PROTECT)),
                ("invited_by", models.ForeignKey(to=settings.AUTH_USER_MODEL,
                                                related_name="sent_staff_invitations",
                                                on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
    ]
