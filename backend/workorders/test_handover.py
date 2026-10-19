from datetime import timedelta
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization,Branch,Membership,User
from crm.models import Customer,Vehicle
from scheduling.models import Appointment,Visit
from workorders.models import WorkOrder
@override_settings(BILLING_ENFORCE_WRITES=False)
class HandoverContracts(TestCase):
    def setUp(self):
        org=Organization.objects.create(name="СТО")
        self.branch=Branch.objects.create(organization=org,name="Основной",code="main")
        u=User.objects.create_user("handover@example.invalid","StrongPassword2026!")
        Membership.objects.create(organization=org,user=u,role="owner")
        c=Customer.objects.create(organization=org,name="Иван")
        v=Vehicle.objects.create(organization=org,make="Kia",model="Rio")
        now=timezone.now()
        ap=Appointment.objects.create(organization=org,branch=self.branch,customer=c,
            vehicle=v,start_at=now,end_at=now+timedelta(hours=1))
        visit=Visit.objects.create(organization=org,branch=self.branch,customer=c,
            vehicle=v,appointment=ap)
        self.order=WorkOrder.objects.create(organization=org,branch=self.branch,
            customer=c,vehicle=v,visit=visit,status="ready",created_by=u)
        self.client=APIClient();self.client.force_authenticate(u)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(org.id)}
    def test_ready_car_is_not_represented_as_delivered(self):
        response=self.client.get(f"/api/v1/workorders/{self.order.id}/handover-readiness",**self.headers)
        self.assertEqual(response.status_code,200,response.content)
        self.assertFalse(response.json()["handover_allowed"])
        self.assertIsNone(response.json()["debt_minor"])
        codes={x["code"]:x for x in response.json()["checks"]}
        self.assertFalse(codes["signatures"]["ok"])
        self.assertFalse(codes["fiscal"]["ok"])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status,"ready")
    def test_other_organization_cannot_query(self):
        other=Organization.objects.create(name="Other")
        response=self.client.get(f"/api/v1/workorders/{self.order.id}/handover-readiness",
            HTTP_X_ORGANIZATION_ID=str(other.id))
        self.assertEqual(response.status_code,404,response.content)
