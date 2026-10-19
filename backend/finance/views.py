from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from core.commands import BusinessConflict,execute_command
from identity.models import Membership,AuditEvent
from identity.scope import TenantAPIView,require_roles
from scheduling.views import valid_branch
from workorders.models import WorkOrder,Estimate
from .models import Invoice,Cashbox,Movement

VIEW=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.CASHIER,Membership.Roles.VIEWER)
MONEY=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.CASHIER)
MANAGE=(Membership.Roles.OWNER,Membership.Roles.MANAGER)

class AmountInput(serializers.Serializer):
    invoice_id=serializers.UUIDField()
    cashbox_id=serializers.UUIDField()
    amount_minor=serializers.IntegerField(min_value=1,max_value=10**12)
    method=serializers.ChoiceField(choices=['cash','card','bank'])
    reference=serializers.CharField(max_length=150)

class RefundInput(serializers.Serializer):
    source_id=serializers.UUIDField()
    amount_minor=serializers.IntegerField(min_value=1,max_value=10**12)
    reference=serializers.CharField(max_length=150)

def display(invoice):
    return {'id':str(invoice.id),'order_id':str(invoice.order_id),
            'amount_minor':invoice.amount_minor,'paid_minor':invoice.paid_minor,
            'refunded_minor':invoice.refunded_minor,
            'debt_minor':invoice.amount_minor-invoice.paid_minor+invoice.refunded_minor}

def record(scope,actor,action,obj):
    AuditEvent.objects.create(organization=scope.organization,actor=actor,
                              event_type='finance.'+action,subject_id=obj.id)

class Cashboxes(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*VIEW)
        branch=valid_branch(self.scope,request.query_params.get('branch_id'))
        return Response([{'id':str(x.id),'name':x.name} for x in
            Cashbox.objects.filter(organization=self.scope.organization,branch=branch)])
    def post(self,request):
        require_roles(self.scope,*MANAGE)
        def operation():
            branch=valid_branch(self.scope,request.data.get('branch_id'))
            name=request.data.get('name')
            if not isinstance(name,str) or not 1<=len(name.strip())<=120:
                raise ValidationError({'name':'Название кассы обязательно.'})
            box=Cashbox.objects.create(organization=self.scope.organization,branch=branch,name=name.strip())
            record(self.scope,request.user,'cashbox',box)
            return {'id':str(box.id),'name':box.name},201
        body,code=execute_command(request,self.scope,'finance.cashbox',operation)
        return Response(body,status=code)

class Invoices(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*VIEW)
        branch=valid_branch(self.scope,request.query_params.get('branch_id'))
        return Response([display(x) for x in Invoice.objects.filter(
            organization=self.scope.organization,branch=branch).order_by('-created_at')[:100]])
    def post(self,request):
        require_roles(self.scope,*MANAGE)
        def operation():
            order=get_object_or_404(WorkOrder,pk=request.data.get('order_id'),organization=self.scope.organization)
            valid_branch(self.scope,order.branch_id)
            if order.status not in ('approved','in_progress','qa','ready'):
                raise BusinessConflict('Начисление допускается только после согласования.')
            if Invoice.objects.filter(order=order).exists():
                raise BusinessConflict('Для заказа уже существует начисление.')
            estimate=Estimate.objects.filter(order=order,state='approved').order_by('-revision').first()
            if estimate is None or estimate.total_minor<=0:
                raise BusinessConflict('Согласованная ненулевая смета обязательна.')
            invoice=Invoice.objects.create(organization=self.scope.organization,branch=order.branch,
                    order=order,estimate=estimate,amount_minor=estimate.total_minor)
            record(self.scope,request.user,'invoice',invoice)
            return display(invoice),201
        body,code=execute_command(request,self.scope,'finance.invoice',operation)
        return Response(body,status=code)

class Payments(TenantAPIView):
    def post(self,request):
        require_roles(self.scope,*MONEY)
        def operation():
            serializer=AmountInput(data=request.data);serializer.is_valid(raise_exception=True)
            d=serializer.validated_data
            invoice=get_object_or_404(Invoice.objects.select_for_update(),
                   pk=d['invoice_id'],organization=self.scope.organization)
            valid_branch(self.scope,invoice.branch_id)
            cashbox=get_object_or_404(Cashbox,pk=d['cashbox_id'],
                   organization=self.scope.organization,branch=invoice.branch)
            if d['amount_minor']>invoice.amount_minor-invoice.paid_minor+invoice.refunded_minor:
                raise BusinessConflict('Сумма превышает непогашенную задолженность.')
            movement=Movement.objects.create(organization=self.scope.organization,branch=invoice.branch,
                invoice=invoice,cashbox=cashbox,kind='income',amount_minor=d['amount_minor'],
                method=d['method'],reference=d['reference'],actor=request.user)
            invoice.paid_minor+=movement.amount_minor
            invoice.save(update_fields=['paid_minor'])
            record(self.scope,request.user,'payment',movement)
            return {'movement_id':str(movement.id),'invoice':display(invoice)},201
        body,code=execute_command(request,self.scope,'finance.payment',operation)
        return Response(body,status=code)

class Refunds(TenantAPIView):
    def post(self,request):
        require_roles(self.scope,*MANAGE)
        def operation():
            serializer=RefundInput(data=request.data);serializer.is_valid(raise_exception=True)
            d=serializer.validated_data
            source=get_object_or_404(Movement,pk=d['source_id'],organization=self.scope.organization,kind='income')
            invoice=Invoice.objects.select_for_update().get(pk=source.invoice_id)
            valid_branch(self.scope,invoice.branch_id)
            already=Movement.objects.filter(source=source,kind='refund').aggregate(total=Sum('amount_minor'))['total'] or 0
            if d['amount_minor']>source.amount_minor-already:
                raise BusinessConflict('Возврат превышает допустимый остаток платежа.')
            movement=Movement.objects.create(organization=self.scope.organization,branch=invoice.branch,
                invoice=invoice,cashbox=source.cashbox,kind='refund',source=source,amount_minor=d['amount_minor'],
                method=source.method,reference=d['reference'],actor=request.user)
            invoice.refunded_minor+=movement.amount_minor
            invoice.save(update_fields=['refunded_minor'])
            record(self.scope,request.user,'refund',movement)
            return {'movement_id':str(movement.id),'invoice':display(invoice)},201
        body,code=execute_command(request,self.scope,'finance.refund',operation)
        return Response(body,status=code)

class Movements(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*VIEW)
        branch=valid_branch(self.scope,request.query_params.get('branch_id'))
        return Response([{'id':str(x.id),'invoice_id':str(x.invoice_id),'kind':x.kind,
            'amount_minor':x.amount_minor,'method':x.method,'reference':x.reference}
            for x in Movement.objects.filter(organization=self.scope.organization,branch=branch)
                 .order_by('-created_at')[:100]])
