from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from core.commands import execute_command,BusinessConflict
from identity.models import Membership
from identity.scope import TenantAPIView,require_roles
from scheduling.views import valid_branch
from .models import WorkOrder,AdditionalWork
from .services import event

EDIT=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.ADVISER)
READ=EDIT+(Membership.Roles.MECHANIC,Membership.Roles.VIEWER)

class AdditionalInput(serializers.Serializer):
    title=serializers.CharField(max_length=200)
    description=serializers.CharField(max_length=3000)
    amount_minor=serializers.IntegerField(min_value=0,max_value=10**12)

def serialize(row):
    return {"id":str(row.pk),"title":row.title,"description":row.description,
            "amount_minor":row.amount_minor,"status":row.status,
            "approval_reference":row.approval_reference}

def order_for(scope,pk):
    order=get_object_or_404(WorkOrder,pk=pk,organization_id=scope.organization_id)
    valid_branch(scope,order.branch_id)
    return order

class AdditionalWorkList(TenantAPIView):
    def get(self,request,pk):
        require_roles(self.scope,*READ)
        order=order_for(self.scope,pk)
        return Response([serialize(x) for x in order.additional_works.order_by("created_at")])
    def post(self,request,pk):
        require_roles(self.scope,*EDIT)
        def operation():
            order=order_for(self.scope,pk)
            if order.status not in ("in_progress","qa"):
                raise BusinessConflict("Дополнительные работы регистрируются в ходе ремонта.")
            data=AdditionalInput(data=request.data);data.is_valid(raise_exception=True)
            row=AdditionalWork.objects.create(order=order,requested_by=request.user,**data.validated_data)
            event(order,request.user,"additional_work_proposed",{"id":str(row.pk)})
            return serialize(row),201
        result,code=execute_command(request,self.scope,"additional_work.propose."+str(pk),operation)
        return Response(result,status=code)

class AdditionalWorkDecision(TenantAPIView):
    def post(self,request,pk,work_id,action):
        require_roles(self.scope,*EDIT)
        if action!="decline":
            raise ValidationError({"action":"Согласование и включение в стоимость доступны только после отдельного подтверждения клиента."})
        def operation():
            order=order_for(self.scope,pk)
            row=get_object_or_404(AdditionalWork,pk=work_id,order=order)
            if row.status!="proposed":
                raise BusinessConflict("Дополнительная работа уже обработана.")
            row.status="declined";row.decided_at=timezone.now()
            row.save(update_fields=["status","decided_at"])
            event(order,request.user,"additional_work_declined",{"id":str(row.pk)})
            return serialize(row),200
        result,code=execute_command(request,self.scope,"additional_work."+str(work_id)+".decline",operation)
        return Response(result,status=code)
