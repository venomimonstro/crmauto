from datetime import timedelta
from uuid import uuid4
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization, Branch, Membership, User
from crm.models import Customer, Vehicle
from scheduling.models import Appointment, Visit
from workorders.models import WorkOrder, Estimate, EstimateLine, OrderDocument

@override_settings(BILLING_ENFORCE_WRITES=False)
class PrintableDocumentContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="СТО А")
        self.branch=Branch.objects.create(organization=self.org, name="Приёмка", code="main")
        self.staff=User.objects.create_user("document-owner@example.invalid", "VeryStrongPassword451244!")
        Membership.objects.create(organization=self.org,user=self.staff,role="owner")
        customer=Customer.objects.create(organization=self.org,name="Иван <script>alert(1)</script>")
        vehicle=Vehicle.objects.create(organization=self.org,make="Audi",model="Q7")
        now=timezone.now()
        appointment=Appointment.objects.create(organization=self.org,branch=self.branch,
            customer=customer,vehicle=vehicle,start_at=now,end_at=now+timedelta(hours=1))
        visit=Visit.objects.create(organization=self.org,branch=self.branch,
            appointment=appointment,customer=customer,vehicle=vehicle)
        self.order=WorkOrder.objects.create(organization=self.org,branch=self.branch,
            visit=visit,customer=customer,vehicle=vehicle,created_by=self.staff,status="draft")
        self.client=APIClient()
        self.client.force_authenticate(self.staff)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.pk)}
    def create_doc(self,kind):
        return self.client.post(f"/api/v1/workorders/{self.order.pk}/documents",
            {"type":kind},format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.headers)
    def test_work_order_snapshot_escaped_and_versioned(self):
        first=self.create_doc("work_order")
        self.assertEqual(first.status_code,201,first.content)
        self.assertEqual(first.json()["revision"],1)
        read=self.client.get(f"/api/v1/workorders/{self.order.pk}/documents/{first.json()['id']}",
                             **self.headers)
        self.assertEqual(read.status_code,200,read.content)
        self.assertIn("&lt;script&gt;",read.json()["html"])
        self.assertNotIn("<script>",read.json()["html"])
        self.assertIn("ПРОЕКТ",read.json()["html"])
        again=self.create_doc("work_order")
        self.assertEqual(again.status_code,201,again.content)
        self.assertEqual(again.json()["revision"],2)
        self.assertEqual(OrderDocument.objects.filter(order=self.order).count(),2)
        self.assertEqual(OrderDocument.objects.get(pk=first.json()["id"]).html_snapshot,read.json()["html"])
    def test_completion_cannot_be_forged_while_draft(self):
        result=self.create_doc("completion")
        self.assertEqual(result.status_code,409,result.content)
        self.assertFalse(OrderDocument.objects.exists())
    def test_foreign_tenant_access_denied(self):
        foreign=Organization.objects.create(name="Чужое СТО")
        membership=Membership.objects.create(organization=foreign,user=self.staff,role="owner")
        self.headers={"HTTP_X_ORGANIZATION_ID":str(foreign.pk)}
        response=self.client.get(f"/api/v1/workorders/{self.order.pk}/documents",**self.headers)
        self.assertEqual(response.status_code,404,response.content)
