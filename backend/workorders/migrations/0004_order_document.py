import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[("workorders","0003_repair_task"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[migrations.CreateModel(name="OrderDocument",fields=[
        ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
        ("doc_type",models.CharField(max_length=20,choices=[("work_order","Заказ-наряд"),("intake","Акт приёмки"),("completion","Акт работ (проект)"),("handover","Акт выдачи (проект)")])),
        ("revision",models.PositiveIntegerField()),
        ("html_snapshot",models.TextField()),
        ("sha256",models.CharField(max_length=64)),
        ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
        ("organization",models.ForeignKey(to="identity.organization",on_delete=django.db.models.deletion.PROTECT)),
        ("order",models.ForeignKey(to="workorders.workorder",related_name="documents",on_delete=django.db.models.deletion.PROTECT)),
        ("created_by",models.ForeignKey(to=settings.AUTH_USER_MODEL,on_delete=django.db.models.deletion.PROTECT)),
    ]),migrations.AddConstraint(model_name="orderdocument",constraint=models.UniqueConstraint(fields=("order","doc_type","revision"),name="wo_document_version_unique"))]
