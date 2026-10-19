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
        unpaid=Invoice.objects.filter(organization=organization,branch=branch).filter(
            paid_minor__lt=F("amount_minor")+F("refunded_minor"))
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


class DailyOperations(TenantAPIView):
    """Owner's actionable operating desk; counts are branch-scoped live data."""
    def get(self,request):
        require_roles(self.scope,*ROLES)
        branch=valid_branch(self.scope,request.query_params.get("branch_id"))
        from scheduling.models import Appointment, Visit
        from procurement.models import PurchaseOrder
        from datetime import datetime,time
        from django.utils import timezone
        day=timezone.localdate()
        start=timezone.make_aware(datetime.combine(day,time.min))
        end=timezone.make_aware(datetime.combine(day+timedelta(days=1),time.min))
        org=self.scope.organization
        appointments=Appointment.objects.filter(organization=org,branch=branch,
                                                 start_at__gte=start,start_at__lt=end)
        orders=WorkOrder.objects.filter(organization=org,branch=branch)
        invoices=Invoice.objects.filter(organization=org,branch=branch)
        visits=Visit.objects.filter(organization=org,branch=branch,status="open")
        stock_reservations=Reservation.objects.filter(organization=org,
            stock__warehouse__branch=branch,state="active")
        moves=Movement.objects.filter(organization=org,branch=branch,
            created_at__gte=start,created_at__lt=end)
        return Response({
            "date":day.isoformat(),"branch_id":str(branch.id),
            "appointments_today":appointments.count(),
            "arrived_today":appointments.filter(status="arrived").count(),
            "open_visits":visits.count(),
            "workorders_waiting_approval":orders.filter(status="awaiting").count(),
            "workorders_in_repair":orders.filter(status="in_progress").count(),
            "workorders_in_quality_check":orders.filter(status="qa").count(),
            "workorders_ready":orders.filter(status="ready").count(),
            "active_parts_reservations":stock_reservations.count(),
            "purchases_waiting_receiving":PurchaseOrder.objects.filter(
                organization=org,branch=branch,status__in=["ordered","partial"]).count(),
            "cash_today_minor":total(moves.filter(kind="income"),"amount_minor")-
                               total(moves.filter(kind="refund"),"amount_minor"),
            "outstanding_minor":sum(max(0,x.amount_minor-x.paid_minor+x.refunded_minor)
                                    for x in invoices.iterator()),
            "warnings":[
                "Отображаются только внутренние данные CRM, не подтверждённые банком.",
                "Готов к выдаче — не значит выдан: закрытие ремонта и документы остаются заблокированы."
            ],
        })
