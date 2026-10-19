"""Read-only pre-handover verification. This does not deliver a vehicle."""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from identity.models import Membership
from identity.scope import TenantAPIView,require_roles
from scheduling.views import valid_branch
from workorders.models import WorkOrder,Estimate,OrderDocument
from finance.models import Invoice
from inventory.models import Reservation
from .documents import json_document

ROLES=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.ADVISER,
       Membership.Roles.VIEWER)
class HandoverReadiness(TenantAPIView):
    def get(self,request,pk):
        require_roles(self.scope,*ROLES)
        order=get_object_or_404(WorkOrder,pk=pk,organization_id=self.scope.organization_id)
        valid_branch(self.scope,order.branch_id)
        checks=[]
        def add(code,passed,description):
            checks.append({"code":code,"ok":bool(passed),"label":description})
        add("ready",order.status=="ready","Заказ-наряд в статусе «Готов к выдаче»")
        add("estimate",Estimate.objects.filter(order=order,state="approved").exists(),
            "Имеется утверждённая смета")
        add("tasks",not order.repair_tasks.filter(state__in=["assigned","running"]).exists(),
            "Нет незавершённых производственных заданий")
        add("additional",not order.additional_works.filter(status="proposed").exists(),
            "Нет дополнительных работ, ожидающих решения")
        add("reservations",not Reservation.objects.filter(order=order,state="active").exists(),
            "Все резервы запчастей выданы или сняты")
        invoice=Invoice.objects.filter(order=order,organization_id=self.scope.organization_id).first()
        debt=max(0,invoice.amount_minor-invoice.paid_minor+invoice.refunded_minor) if invoice else None
        add("invoice",invoice is not None,"Начисление сформировано")
        add("settlement",invoice is not None and debt==0,"Внутренняя задолженность погашена")
        docs=OrderDocument.objects.filter(order=order,organization_id=self.scope.organization_id)
        add("intake",docs.filter(doc_type="intake").exists(),"Сформирован акт приёмки (проект)")
        add("completion",docs.filter(doc_type="completion").exists(),
            "Сформирован акт выполненных работ (проект)")
        add("handover",docs.filter(doc_type="handover").exists(),"Подготовлен акт выдачи (проект)")
        # A generated draft is NOT an authenticated signed document or fiscal proof.
        add("signatures",False,"Не подтверждены подписи клиента и исполнителя")
        add("fiscal",False,"Не подключена проверка фискального чека")
        return Response({"order_id":str(order.id),"status":order.status,
            "checks":checks,"operational_checks_passed":all(x["ok"] for x in checks),
            "handover_allowed":False,"debt_minor":debt,
            "message":"Выдача автомобиля не разрешена, пока не завершён фискальный и подписной контур."})
