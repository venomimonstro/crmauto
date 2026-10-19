import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations,models
from django.db.models import Q

class Migration(migrations.Migration):
    dependencies=[("workorders","0002_additional_work"),("identity","0001_initial")]
    operations=[migrations.CreateModel(name="RepairTask",fields=[
        ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
        ("title",models.CharField(max_length=200)),
        ("state",models.CharField(max_length=12,default="assigned",choices=[
            ("assigned","Назначено"),("running","В работе"),("done","Выполнено"),("cancelled","Отменено")])),
        ("started_at",models.DateTimeField(null=True,blank=True)),
        ("completed_at",models.DateTimeField(null=True,blank=True)),
        ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
        ("order",models.ForeignKey(to="workorders.workorder",related_name="repair_tasks",on_delete=django.db.models.deletion.PROTECT)),
        ("mechanic",models.ForeignKey(to="identity.membership",on_delete=django.db.models.deletion.PROTECT)),
    ]),migrations.AddConstraint(model_name="repairtask",
       constraint=models.UniqueConstraint(fields=["mechanic"],condition=Q(state="running"),
                                          name="wo_one_running_task_per_mechanic")),
       migrations.AddConstraint(model_name="repairtask",
       constraint=models.CheckConstraint(condition=Q(completed_at__isnull=True)|Q(started_at__isnull=False),
                                        name="wo_task_end_requires_start"))]
