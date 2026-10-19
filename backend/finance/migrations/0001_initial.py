import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations,models
from django.db.models import Q,F

class Migration(migrations.Migration):
    initial=True
    dependencies=[('identity','0001_initial'),('workorders','0001_initial'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(name='Invoice',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('amount_minor',models.PositiveBigIntegerField()),
            ('paid_minor',models.PositiveBigIntegerField(default=0)),
            ('refunded_minor',models.PositiveBigIntegerField(default=0)),
            ('created_at',models.DateTimeField(default=django.utils.timezone.now)),
            ('organization',models.ForeignKey(to='identity.organization',on_delete=django.db.models.deletion.PROTECT)),
            ('branch',models.ForeignKey(to='identity.branch',on_delete=django.db.models.deletion.PROTECT)),
            ('order',models.OneToOneField(to='workorders.workorder',on_delete=django.db.models.deletion.PROTECT)),
            ('estimate',models.OneToOneField(to='workorders.estimate',on_delete=django.db.models.deletion.PROTECT))]),
        migrations.CreateModel(name='Cashbox',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('name',models.CharField(max_length=120)),
            ('organization',models.ForeignKey(to='identity.organization',on_delete=django.db.models.deletion.PROTECT)),
            ('branch',models.ForeignKey(to='identity.branch',on_delete=django.db.models.deletion.PROTECT))]),
        migrations.CreateModel(name='Movement',fields=[
            ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ('kind',models.CharField(max_length=6,choices=[('income','Приход'),('refund','Возврат')])),
            ('amount_minor',models.PositiveBigIntegerField()),
            ('method',models.CharField(max_length=10,choices=[('cash','Наличные'),('card','Карта'),('bank','Банк')])),
            ('reference',models.CharField(max_length=150)),
            ('created_at',models.DateTimeField(default=django.utils.timezone.now)),
            ('organization',models.ForeignKey(to='identity.organization',on_delete=django.db.models.deletion.PROTECT)),
            ('branch',models.ForeignKey(to='identity.branch',on_delete=django.db.models.deletion.PROTECT)),
            ('invoice',models.ForeignKey(to='finance.invoice',related_name='movements',on_delete=django.db.models.deletion.PROTECT)),
            ('cashbox',models.ForeignKey(to='finance.cashbox',on_delete=django.db.models.deletion.PROTECT)),
            ('actor',models.ForeignKey(to=settings.AUTH_USER_MODEL,on_delete=django.db.models.deletion.PROTECT)),
            ('source',models.ForeignKey(to='finance.movement',null=True,blank=True,on_delete=django.db.models.deletion.PROTECT))]),
        migrations.AddConstraint(model_name='invoice',constraint=models.CheckConstraint(condition=Q(paid_minor__lte=F('amount_minor')),name='fin_paid_limit')),
        migrations.AddConstraint(model_name='invoice',constraint=models.CheckConstraint(condition=Q(refunded_minor__lte=F('paid_minor')),name='fin_refund_limit')),
        migrations.AddConstraint(model_name='cashbox',constraint=models.UniqueConstraint(fields=['branch','name'],name='fin_unique_box')),
        migrations.AddConstraint(model_name='movement',constraint=models.CheckConstraint(condition=Q(amount_minor__gt=0),name='fin_positive_movement')),
    ]
