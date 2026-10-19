from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from core.commands import BusinessConflict,execute_command
from identity.models import Membership,MemberBranch
from identity.scope import TenantAPIView,require_roles
from scheduling.views import valid_branch
from .models import WorkOrder,RepairTask
from .services import event

ADMIN=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.ADVISER)
READ=ADMIN+(Membership.Roles.MECHANIC,Membership.Roles.VIEWER)

class TaskInput(serializers.Serializer):
    membership_id=serializers.UUIDField()
    title=serializers.CharField(max_length=200)

def data(x):
    return {"id":str(x.id),"order_id":str(x.order_id),"mechanic_id":str(x.mechanic_id),
        "title":x.title,"state":x.state,
        "started_at":x.started_at.isoformat() if x.started_at else None,
        "completed_at":x.completed_at.isoformat() if x.completed_at else None}

class Tasks(TenantAPIView):
    def get(self,request,pk):
        require_roles(self.scope,*READ)
        order=get_object_or_404(WorkOrder,pk=pk,organization_id=self.scope.organization_id)
        valid_branch(self.scope,order.branch_id)
        rows=RepairTask.objects.filter(order=order).order_by("created_at")
        if self.scope.membership.role==Membership.Roles.MECHANIC:
            rows=rows.filter(mechanic=self.scope.membership)
        return Response([data(x) for x in rows])
    def post(self,request,pk):
        require_roles(self.scope,*ADMIN)
        def operation():
            order=get_object_or_404(WorkOrder,pk=pk,organization_id=self.scope.organization_id)
            valid_branch(self.scope,order.branch_id)
            if order.status not in ("approved","in_progress"):
                raise BusinessConflict("Задания создаются только для согласованного ремонта.")
            s=TaskInput(data=request.data);s.is_valid(raise_exception=True)
            member=get_object_or_404(Membership,pk=s.validated_data["membership_id"],
                  organization_id=self.scope.organization_id,is_active=True,role=Membership.Roles.MECHANIC)
            if not MemberBranch.objects.filter(membership=member,branch_id=order.branch_id).exists():
                raise BusinessConflict("Механик не состоит в филиале.")
            task=RepairTask.objects.create(order=order,mechanic=member,title=s.validated_data["title"])
            event(order,request.user,"task_assigned",{"task_id":str(task.id)})
            return data(task),201
        result,code=execute_command(request,self.scope,"repair.task.assign."+str(pk),operation)
        return Response(result,status=code)

class TaskAction(TenantAPIView):
    def post(self,request,pk,task_id,action):
        require_roles(self.scope,*READ)
        if action not in ("start","finish","cancel"):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"action":"Неизвестная операция."})
        def operation():
            order=get_object_or_404(WorkOrder,pk=pk,organization_id=self.scope.organization_id)
            valid_branch(self.scope,order.branch_id)
            task=get_object_or_404(RepairTask,pk=task_id,order=order)
            is_manager=self.scope.membership.role in ADMIN
            if not is_manager and task.mechanic_id!=self.scope.membership.pk:
                raise PermissionDenied("Можно изменять только свои задания.")
            if action=="start":
                if order.status!="in_progress" or task.state!="assigned":
                    raise BusinessConflict("Начало возможно только при активном ремонте.")
                if RepairTask.objects.filter(mechanic=task.mechanic,state="running").exists():
                    raise BusinessConflict("У механика уже есть активное задание.")
                task.started_at=timezone.now();task.state="running"
                task.save(update_fields=["state","started_at"])
            elif action=="finish":
                if order.status not in ("in_progress","qa") or task.state!="running":
                    raise BusinessConflict("Задание не выполняется.")
                task.completed_at=timezone.now();task.state="done"
                task.save(update_fields=["state","completed_at"])
            else:
                if not is_manager or task.state!="assigned":
                    raise BusinessConflict("Отменить можно только неначатое задание.")
                task.state="cancelled";task.save(update_fields=["state"])
            event(order,request.user,"task_"+action,{"task_id":str(task.id)})
            return data(task),200
        result,code=execute_command(request,self.scope,
           "repair.task."+str(task_id)+"."+action,operation)
        return Response(result,status=code)
