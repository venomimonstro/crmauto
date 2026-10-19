import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations,models
class Migration(migrations.Migration):
    initial=True
    dependencies=[('identity','0001_initial'),('crm','0001_initial'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[migrations.CreateModel(name='PortalGrant',fields=[
        ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
        ('active',models.BooleanField(default=False)),
        ('verification_reference',models.CharField(max_length=250)),
        ('created_at',models.DateTimeField(default=django.utils.timezone.now)),
        ('organization',models.ForeignKey(to='identity.organization',on_delete=django.db.models.deletion.PROTECT)),
        ('customer',models.ForeignKey(to='crm.customer',on_delete=django.db.models.deletion.PROTECT)),
        ('user',models.ForeignKey(to=settings.AUTH_USER_MODEL,on_delete=django.db.models.deletion.PROTECT)),
        ('verified_by',models.ForeignKey(to=settings.AUTH_USER_MODEL,related_name='portal_grants_verified',on_delete=django.db.models.deletion.PROTECT)),
    ]),migrations.AddConstraint(model_name='portalgrant',constraint=models.UniqueConstraint(fields=('organization','customer','user'),name='portal_grant_unique'))]
