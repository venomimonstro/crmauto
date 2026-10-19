"""Authenticated customer portal approval for an existing verified, active PortalGrant.
This is an auditable account decision, NOT a qualified electronic signature.
"""
from django.db import transaction
from django.db.models import Exists,OuterRef,F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from core.commands import BusinessConflict
from identity.models import AuditEvent
from portal.models import PortalGrant
from workorders.models import WorkOrder,Estimate
from workorders.services import change

class PortalEstimateDecision(APIView):
    permission_classes=[IsAuthenticated]
    @transaction.atomic
    def post(self,request,pk):
        if request.data.get("decision") not in ("approve","reject"):
            raise ValidationError({"decision":"Выберите approve или reject."})
        grant=PortalGrant.objects.filter(user=request.user,active=True,
            organization_id=OuterRef("organization_id"),customer_id=OuterRef("customer_id"),
            organization__is_active=True,customer__organization_id=OuterRef("organization_id"),
            customer__archived_at__isnull=True)
        order=get_object_or_404(WorkOrder.objects.select_for_update().annotate(
            access=Exists(grant)).filter(access=True),pk=pk)
        estimate=Estimate.objects.select_for_update().filter(order=order,state="submitted").order_by("-revision").first()
        if order.status!="awaiting" or not estimate:
            raise BusinessConflict("Нет ожидающей согласования сметы.")
        try: revision=int(request.data.get("revision",0))
        except (ValueError,TypeError): revision=0
        if revision!=estimate.revision:
            raise BusinessConflict("Редакция сметы изменилась. Обновите страницу.")
        if request.data["decision"]=="approve":
            estimate.state="approved"
            estimate.approved_at=timezone.now()
            estimate.approval_method="authenticated_customer_portal"
            estimate.approval_reference="portal:user:"+str(request.user.pk)
            estimate.save(update_fields=["state","approved_at","approval_method","approval_reference"])
            change(order,request.user,"approved")
        else:
            estimate.state="rejected";estimate.save(update_fields=["state"])
            change(order,request.user,"draft","Отказ клиента через личный кабинет")
        AuditEvent.objects.create(organization=order.organization,actor=request.user,
            event_type="portal.estimate_decision",subject_id=estimate.pk,
            details={"order_id":str(order.pk),"revision":revision,"decision":request.data["decision"]})
        return Response({"order_id":str(order.pk),"revision":revision,
                         "decision":request.data["decision"],"status":order.status,
                         "signature_status":"not_qualified_electronic_signature"})
