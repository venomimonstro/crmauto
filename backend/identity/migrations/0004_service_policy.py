import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations,models
from django.db.models import Q
class Migration(migrations.Migration):
    dependencies=[("identity","0003_organization_legal_profile"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[migrations.CreateModel(name="ServicePolicy",fields=[
        ("id",models.UUIDField(default=uuid.uuid4,primary_key=True,editable=False,serialize=False)),
        ("version",models.PositiveIntegerField()),
        ("service_terms",models.TextField()),
        ("warranty_terms",models.TextField()),
        ("is_current",models.BooleanField(default=True)),
        ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
        ("organization",models.ForeignKey(to="identity.organization",on_delete=django.db.models.deletion.PROTECT)),
        ("created_by",models.ForeignKey(to=settings.AUTH_USER_MODEL,on_delete=django.db.models.deletion.PROTECT)),
    ]),migrations.AddConstraint(model_name="servicepolicy",
        constraint=models.UniqueConstraint(fields=["organization","version"],name="service_policy_version_unique")),
       migrations.AddConstraint(model_name="servicepolicy",
        constraint=models.UniqueConstraint(fields=["organization"],condition=Q(is_current=True),name="service_policy_one_current"))]
