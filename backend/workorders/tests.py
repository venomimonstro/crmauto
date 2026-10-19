import uuid
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from crm.models import Customer,Vehicle
from identity.models import Organization,Branch,Membership,User
from scheduling.models import Appointment,Visit
from .models import WorkOrder,Estimate,EstimateLine

class WorkOrderContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="СТО А")
        self.other=Organization.objects.create(name="СТО Б")
        self.branch=Branch.objects.create(organization=self.org,code="main",name="Основной")
        self.user=User.objects.create_user("master@test.invalid","SafePasswordForTesting7788!")
        Membership.objects.create(organization=self.org,user=self.user,role="adviser")
        self.customer=Customer.objects.create(organization=self.org,name="Иван")
        self.car=Vehicle.objects.create(organization=self.org,make="Ford",model="Focus")
        now=timezone.now()
        self.appointment=Appointment.objects.create(organization=self.org,branch=self.branch,
            customer=self.customer,vehicle=self.car,start_at=now,end_at=now+timedelta(hours=2),status="arrived")
        self.visit=Visit.objects.create(organization=self.org,branch=self.branch,
            appointment=self.appointment,customer=self.customer,vehicle=self.car)
        self.client=APIClient()
        self.client.force_authenticate(self.user)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}

    def post(self,path,data=None,key=None):
        return self.client.post(path,data or {},format="json",
            HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),**self.headers)

    def create_order(self):
        response=self.post("/api/v1/workorders",{"visit_id":str(self.visit.id),"complaint":"Стук подвески"})
        self.assertEqual(response.status_code,201,response.content)
        return response.json()["id"]

    def line(self,order):
        return self.post(f"/api/v1/workorders/{order}/lines",
                         {"kind":"labor","title":"Диагностика","quantity":"1.500","unit_price_minor":120000})

    def test_creation_is_idempotent_and_one_per_visit(self):
        key=str(uuid.uuid4())
        data={"visit_id":str(self.visit.id)}
        first=self.post("/api/v1/workorders",data,key)
        repeated=self.post("/api/v1/workorders",data,key)
        self.assertEqual(first.status_code,201)
        self.assertEqual(first.json(),repeated.json())
        self.assertEqual(WorkOrder.objects.count(),1)
        self.assertEqual(self.post("/api/v1/workorders",data).status_code,409)

    def test_cannot_start_before_approval(self):
        order=self.create_order()
        self.assertEqual(self.post(f"/api/v1/workorders/{order}/actions/start").status_code,409)
        self.assertEqual(WorkOrder.objects.get(id=order).status,"draft")

    def test_approval_requires_reference_and_preserves_revision(self):
        order=self.create_order()
        self.assertEqual(self.line(order).status_code,201)
        self.assertEqual(self.post(f"/api/v1/workorders/{order}/actions/submit").status_code,200)
        self.assertEqual(self.line(order).status_code,409)
        missing=self.post(f"/api/v1/workorders/{order}/actions/approve")
        self.assertEqual(missing.status_code,400)
        self.assertEqual(self.post(f"/api/v1/workorders/{order}/actions/approve",
                                  {"reference":"Подписанный акт согласования #123"}).status_code,200)
        self.assertEqual(self.post(f"/api/v1/workorders/{order}/actions/start").status_code,200)
        self.assertEqual(EstimateLine.objects.filter(estimate__order_id=order).count(),1)
        self.assertEqual(Estimate.objects.get(order_id=order).total_minor,180000)

    def test_reject_then_edit_is_new_revision(self):
        order=self.create_order()
        self.line(order)
        self.post(f"/api/v1/workorders/{order}/actions/submit")
        self.assertEqual(self.post(f"/api/v1/workorders/{order}/actions/reject").status_code,200)
        self.assertEqual(self.post(f"/api/v1/workorders/{order}/actions/revise").status_code,409)
        # Explicitly creating new revision after a rejection is part of draft edits.
        self.assertEqual(WorkOrder.objects.get(id=order).status,"draft")

    def test_cross_company_visit_hidden(self):
        other_customer=Customer.objects.create(organization=self.other,name="Чужой")
        other_vehicle=Vehicle.objects.create(organization=self.other,make="Audi",model="A4")
        other_branch=Branch.objects.create(organization=self.other,code="b",name="Чужой филиал")
        a=Appointment.objects.create(organization=self.other,branch=other_branch,
             customer=other_customer,vehicle=other_vehicle,
             start_at=timezone.now(),end_at=timezone.now()+timedelta(hours=1),status="arrived")
        visit=Visit.objects.create(organization=self.other,branch=other_branch,
                                  appointment=a,customer=other_customer,vehicle=other_vehicle)
        response=self.post("/api/v1/workorders",{"visit_id":str(visit.id)})
        self.assertEqual(response.status_code,404)
        self.assertEqual(WorkOrder.objects.count(),0)

    def test_cannot_deliver_without_financial_module(self):
        order=self.create_order()
        self.line(order)
        self.post(f"/api/v1/workorders/{order}/actions/submit")
        self.post(f"/api/v1/workorders/{order}/actions/approve",{"reference":"Подпись #2"})
        self.post(f"/api/v1/workorders/{order}/actions/start")
        self.post(f"/api/v1/workorders/{order}/actions/qa")
        self.post(f"/api/v1/workorders/{order}/actions/ready")
        self.assertEqual(self.post(f"/api/v1/workorders/{order}/actions/deliver").status_code,409)
