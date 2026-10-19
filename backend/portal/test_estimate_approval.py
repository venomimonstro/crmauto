from datetime import timedelta
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization,Branch,Membership,User
from crm.models import Customer,Vehicle
from scheduling.models import Appointment,Visit
from workorders.models import WorkOrder,Estimate
from portal.models import PortalGrant

@override_settings(BILLING_ENFORCE_WRITES=False)
class CustomerEstimateApproval(TestCase):
    def setUp(self):
        org=Organization.objects.create(name="СТО")
        branch=Branch.objects.create(organization=org,name="Центр",code="main")
        adviser=User.objects.create_user("service@invalid.test","LongPassword998877!")
        self.customer_user=User.objects.create_user("customer@invalid.test","LongPassword998877!")
        self.stranger=User.objects.create_user("stranger@invalid.test","LongPassword998877!")
        Membership.objects.create(organization=org,user=adviser,role="owner")
        customer=Customer.objects.create(organization=org,name="Покупатель")
        car=Vehicle.objects.create(organization=org,make="Volvo",model="XC90")
        now=timezone.now()
        appointment=Appointment.objects.create(organization=org,branch=branch,customer=customer,
           vehicle=car,start_at=now,end_at=now+timedelta(hours=1))
        visit=Visit.objects.create(organization=org,branch=branch,customer=customer,
           vehicle=car,appointment=appointment)
        self.order=WorkOrder.objects.create(organization=org,branch=branch,customer=customer,
           vehicle=car,visit=visit,created_by=adviser,status="awaiting")
        self.estimate=Estimate.objects.create(order=self.order,state="submitted",revision=1,total_minor=80000)
        PortalGrant.objects.create(organization=org,customer=customer,user=self.customer_user,
           active=True,verified_by=adviser,verification_reference="verified in person")
        self.client=APIClient()
    def decision(self,user,revision=1,choice="approve"):
        self.client.force_authenticate(user)
        return self.client.post(f"/api/v1/portal/orders/{self.order.id}/estimate-decision",
             {"revision":revision,"decision":choice},format="json")
    def test_customer_approves_only_once(self):
        result=self.decision(self.customer_user)
        self.assertEqual(result.status_code,200,result.content)
        self.estimate.refresh_from_db()
        self.assertEqual(self.estimate.approval_method,"authenticated_customer_portal")
        self.assertEqual(self.estimate.state,"approved")
        self.assertEqual(self.decision(self.customer_user).status_code,409)
    def test_stranger_cannot_approve(self):
        result=self.decision(self.stranger)
        self.assertEqual(result.status_code,404,result.content)
        self.estimate.refresh_from_db();self.assertEqual(self.estimate.state,"submitted")
    def test_stale_revision_rejected(self):
        self.assertEqual(self.decision(self.customer_user,revision=2).status_code,409)
        self.estimate.refresh_from_db();self.assertEqual(self.estimate.state,"submitted")
    def test_customer_rejects_without_approval(self):
        result=self.decision(self.customer_user,choice="reject")
        self.assertEqual(result.status_code,200,result.content)
        self.order.refresh_from_db();self.assertEqual(self.order.status,"draft")
        self.estimate.refresh_from_db();self.assertEqual(self.estimate.state,"rejected")
