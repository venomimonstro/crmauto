import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations,models
from django.db.models import Q,F

class Migration(migrations.Migration):
    initial=True
    dependencies=[('identity','0001_initial'),('crm','0001_initial')]
    operations=[
        migrations.CreateModel(name='Shift',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('begins',models.DateTimeField()),('ends',models.DateTimeField()),
            ('state',models.CharField(max_length=12,default='planned',choices=[('planned','Плановая'),('completed','Завершена'),('cancelled','Отменена')])),
            ('organization',models.ForeignKey(to='identity.organization',on_delete=django.db.models.deletion.PROTECT)),
            ('branch',models.ForeignKey(to='identity.branch',on_delete=django.db.models.deletion.PROTECT)),
            ('membership',models.ForeignKey(to='identity.membership',on_delete=django.db.models.deletion.PROTECT))]),
        migrations.CreateModel(name='TireSet',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('code',models.CharField(max_length=80)),('pieces',models.PositiveSmallIntegerField()),
            ('description',models.CharField(max_length=300)),('storage_location',models.CharField(max_length=120)),
            ('received_at',models.DateTimeField(default=django.utils.timezone.now)),
            ('released_at',models.DateTimeField(null=True,blank=True)),
            ('state',models.CharField(max_length=12,default='stored',choices=[('stored','Хранится'),('released','Выдан')])),
            ('organization',models.ForeignKey(to='identity.organization',on_delete=django.db.models.deletion.PROTECT)),
            ('branch',models.ForeignKey(to='identity.branch',on_delete=django.db.models.deletion.PROTECT)),
            ('customer',models.ForeignKey(to='crm.customer',on_delete=django.db.models.deletion.PROTECT)),
            ('vehicle',models.ForeignKey(to='crm.vehicle',null=True,blank=True,on_delete=django.db.models.deletion.PROTECT))]),
        migrations.AddConstraint(model_name='shift',constraint=models.CheckConstraint(condition=Q(ends__gt=F('begins')),name='workforce_shift_time_valid')),
        migrations.AddConstraint(model_name='tireset',constraint=models.UniqueConstraint(fields=('organization','code'),name='workforce_tireset_code')),
        migrations.AddConstraint(model_name='tireset',constraint=models.CheckConstraint(condition=Q(pieces__gte=1,pieces__lte=16),name='workforce_tireset_pieces')),
    ]
