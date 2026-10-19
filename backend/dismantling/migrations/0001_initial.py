import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations,models
from django.db.models import Q

class Migration(migrations.Migration):
    initial=True
    dependencies=[('identity','0001_initial'),('inventory','0001_initial'),('workorders','0001_initial')]
    operations=[
      migrations.CreateModel(name='Donor',fields=[
        ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
        ('vin',models.CharField(max_length=17,blank=True)),
        ('description',models.CharField(max_length=250)),
        ('acquisition_cost_minor',models.PositiveBigIntegerField()),
        ('extra_cost_minor',models.PositiveBigIntegerField(default=0)),
        ('created_at',models.DateTimeField(default=django.utils.timezone.now)),
        ('organization',models.ForeignKey(to='identity.organization',on_delete=django.db.models.deletion.PROTECT)),
        ('branch',models.ForeignKey(to='identity.branch',on_delete=django.db.models.deletion.PROTECT))]),
      migrations.CreateModel(name='StorageBin',fields=[
        ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
        ('code',models.CharField(max_length=64)),
        ('organization',models.ForeignKey(to='identity.organization',on_delete=django.db.models.deletion.PROTECT)),
        ('warehouse',models.ForeignKey(to='inventory.warehouse',on_delete=django.db.models.deletion.PROTECT))]),
      migrations.CreateModel(name='SalvagedPart',fields=[
        ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
        ('inventory_code',models.CharField(max_length=80)),('name',models.CharField(max_length=200)),
        ('condition_notes',models.CharField(max_length=500,blank=True)),
        ('allocated_cost_minor',models.PositiveBigIntegerField(default=0)),
        ('target_price_minor',models.PositiveBigIntegerField(default=0)),
        ('state',models.CharField(max_length=12,default='recorded',choices=[('recorded','Демонтирована'),('available','Готова к продаже'),('reserved','Зарезервирована'),('retired','Списана')])),
        ('created_at',models.DateTimeField(default=django.utils.timezone.now)),
        ('organization',models.ForeignKey(to='identity.organization',on_delete=django.db.models.deletion.PROTECT)),
        ('donor',models.ForeignKey(to='dismantling.donor',related_name='parts',on_delete=django.db.models.deletion.PROTECT)),
        ('bin',models.ForeignKey(to='dismantling.storagebin',on_delete=django.db.models.deletion.PROTECT)),
        ('reserved_order',models.ForeignKey(to='workorders.workorder',null=True,blank=True,on_delete=django.db.models.deletion.PROTECT))]),
      migrations.AddConstraint(model_name='storagebin',constraint=models.UniqueConstraint(fields=('warehouse','code'),name='dismantling_bin_unique')),
      migrations.AddConstraint(model_name='salvagedpart',constraint=models.UniqueConstraint(fields=('organization','inventory_code'),name='dismantling_unique_part_code')),
      migrations.AddConstraint(model_name='salvagedpart',constraint=models.CheckConstraint(condition=Q(state='reserved',reserved_order__isnull=False) | ~Q(state='reserved'),name='dismantling_reservation_link')),
    ]
