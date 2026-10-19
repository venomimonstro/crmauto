import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q,F
from django.utils import timezone

class Invoice(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('identity.Organization',on_delete=models.PROTECT)
    branch=models.ForeignKey('identity.Branch',on_delete=models.PROTECT)
    order=models.OneToOneField('workorders.WorkOrder',on_delete=models.PROTECT)
    estimate=models.OneToOneField('workorders.Estimate',on_delete=models.PROTECT)
    amount_minor=models.PositiveBigIntegerField()
    paid_minor=models.PositiveBigIntegerField(default=0)
    refunded_minor=models.PositiveBigIntegerField(default=0)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[
          models.CheckConstraint(condition=Q(paid_minor__lte=F('amount_minor')+F('refunded_minor')),name='fin_paid_limit'),
          models.CheckConstraint(condition=Q(refunded_minor__lte=F('paid_minor')),name='fin_refund_limit')]

class Cashbox(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('identity.Organization',on_delete=models.PROTECT)
    branch=models.ForeignKey('identity.Branch',on_delete=models.PROTECT)
    name=models.CharField(max_length=120)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['branch','name'],name='fin_unique_box')]

class Movement(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('identity.Organization',on_delete=models.PROTECT)
    branch=models.ForeignKey('identity.Branch',on_delete=models.PROTECT)
    invoice=models.ForeignKey(Invoice,on_delete=models.PROTECT,related_name='movements')
    cashbox=models.ForeignKey(Cashbox,on_delete=models.PROTECT)
    kind=models.CharField(max_length=6,choices=[('income','Приход'),('refund','Возврат')])
    amount_minor=models.PositiveBigIntegerField()
    method=models.CharField(max_length=10,choices=[('cash','Наличные'),('card','Карта'),('bank','Банк')])
    reference=models.CharField(max_length=150)
    source=models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(amount_minor__gt=0),name='fin_positive_movement')]
