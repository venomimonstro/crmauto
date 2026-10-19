import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations,models
class Migration(migrations.Migration):
    dependencies=[("workorders","0001_initial"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[migrations.CreateModel(name="AdditionalWork",fields=[
      ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
      ("title",models.CharField(max_length=200)),
      ("description",models.TextField()),
      ("amount_minor",models.PositiveBigIntegerField()),
      ("status",models.CharField(max_length=16,default="proposed",choices=[
          ("proposed","Предложена"),("declined","Отклонена"),("approved","Подтверждена")])),
      ("approval_reference",models.CharField(max_length=250,blank=True)),
      ("created_at",models.DateTimeField(default=django.utils.timezone.now)),
      ("decided_at",models.DateTimeField(blank=True,null=True)),
      ("order",models.ForeignKey(to="workorders.workorder",related_name="additional_works",on_delete=django.db.models.deletion.PROTECT)),
      ("requested_by",models.ForeignKey(to=settings.AUTH_USER_MODEL,on_delete=django.db.models.deletion.PROTECT)),
    ])]
