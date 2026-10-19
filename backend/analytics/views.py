from django.db.models import Sum, F
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from identity.models import Membership
from identity.scope import TenantAPIView, require_roles
from scheduling.views import valid_branch
from finance.models import Invoice, Movement
from inventory.models import Stock, Reservation
from workorders.models import WorkOrder
from django.utils import timezone
from datetime import timedelta

ROLES=(Membership.Roles.OWNER, Membership.Roles.MANAGER, Membership.Roles.VIEWER)

def total(qs, field):
    return qs.aggregate(value=Sum(field))["value"] or 0

def metrics(org, branch):
    invoices=Invoice.objects.filter(organization=org,branch=branch)
    movements=Movement.objects.filter(organization=org,branch=branch)
    income=total(movements.filter(kind="income"),"amount_minor")
    refunds=total(movements.filter(kind="refund"),"amount_minor")
    billed=total(invoices,"amount_minor")
    debt=sum(max(0,item.amount_minor-item.paid_minor+item.refunded_minor) for item in invoices.iterator())
    return {
      "currency":"RUB",
      "invoiced_minor":billed,
      "cash_received_minor":income,
      "cash_refunded_minor":refunds,
      "net_cash_minor":income-refunds,
      "outstanding_minor":debt,
      "invoice_count":invoices.count(),
      "profit_minor":None,
      "profit_unavailable_reason":"Нет подтверждённой себестоимости партий, оплаты труда и прочих расходов.",
      "accounting_scope":"Внутренний журнал CRM; не банковская сверка и не фискальные данные."
    }

class FinanceSummary(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*ROLES)
        branch=valid_branch(self.scope,request.query_params.get("branch_id"))
        return Response(metrics(self.scope.organization,branch))

class LossCenter(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*ROLES)
        branch=valid_branch(self.scope,request.query_params.get("branch_id"))
        organization=self.scope.organization
        unpaid=Invoice.objects.filter(organization=organization,branch=branch,paid_minor__lt=F("amount_minor"))
        stalled=WorkOrder.objects.filter(organization=organization,branch=branch,
            status__in=["awaiting","in_progress","qa"],created_at__lt=timezone.now()-timedelta(days=7))
        reserved=Reservation.objects.filter(organization=organization,stock__warehouse__branch=branch,
            state="active",created_at__lt=timezone.now()-timedelta(days=3))
        rows=[]
        for item in unpaid.order_by("created_at")[:50]:
            debt=item.amount_minor-item.paid_minor+item.refunded_minor
            if debt>0: rows.append({"code":"unpaid_invoice","severity":"high",
                "object_id":str(item.id),"amount_minor":debt,
                "description":"Непогашенная задолженность по начислению."})
        for item in stalled.order_by("created_at")[:50]:
            rows.append({"code":"stalled_order","severity":"medium","object_id":str(item.id),
                "amount_minor":None,"description":"Заказ-наряд без завершения более 7 суток."})
        for item in reserved.order_by("created_at")[:50]:
            rows.append({"code":"stale_reservation","severity":"medium","object_id":str(item.id),
                "amount_minor":None,"description":"Резерв запчастей старше 3 суток."})
        return Response({"items":rows,"partial":True,
            "limitations":["Правила демонстрационные: SLA и пороги настраиваются позже.",
              "Неоплаченный документ не всегда является просроченным долгом.",
              "Нельзя оценить стоимость потерь без достоверной себестоимости."]})
