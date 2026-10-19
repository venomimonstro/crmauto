from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization, Branch, User, Membership
from crm.models import Customer, Vehicle
from scheduling.models import Appointment, Visit
from workorders.models import WorkOrder, Estimate
from finance.models import Invoice

@override_settings(BILLING_ENFORCE_WRITES=False)
class LossCenterRefundRegression(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="First Shop")
        self.other=Organization.objects.create(name="Other Shop")
        self.branch=Branch.objects.create(organization=self.org,name="Main",code="main")
        self.other_branch=Branch.objects.create(organization=self.other,name="Main",code="other")
        self.user=User.objects.create_user("loss@test.invalid","StrongLongPassword917261!")
        Membership.objects.create(organization=self.org,user=self.user,role="owner")
        self.client=APIClient()
        self.client.force_authenticate(self.user)

    def test_partial_refund_restores_debt_and_tenant_separation(self):
        customer=Customer.objects.create(organization=self.org,name="Client")
        vehicle=Vehicle.objects.create(organization=self.org,make="Toyota",model="Camry")
        now=timezone.now()
        appointment=Appointment.objects.create(organization=self.org,branch=self.branch,
            customer=customer,vehicle=vehicle,start_at=now,end_at=now+timedelta(hours=1))
        visit=Visit.objects.create(organization=self.org,branch=self.branch,
            appointment=appointment,customer=customer,vehicle=vehicle)
        order=WorkOrder.objects.create(organization=self.org,branch=self.branch,
            visit=visit,customer=customer,vehicle=vehicle,created_by=self.user,status="approved")
        estimate=Estimate.objects.create(order=order,revision=1,state="approved",total_minor=10000)
        invoice=Invoice.objects.create(organization=self.org,branch=self.branch,
            order=order,estimate=estimate,amount_minor=10000,paid_minor=10000,refunded_minor=3000)
        result=self.client.get("/api/v1/reports/losses?branch_id="+str(self.branch.pk),
            HTTP_X_ORGANIZATION_ID=str(self.org.pk))
        self.assertEqual(result.status_code,200,result.content)
        debt=[x for x in result.json()["items"] if x["code"]=="unpaid_invoice" and x["object_id"]==str(invoice.pk)]
        self.assertEqual(len(debt),1)
        self.assertEqual(debt[0]["amount_minor"],3000)
        foreign=self.client.get("/api/v1/reports/losses?branch_id="+str(self.other_branch.pk),
            HTTP_X_ORGANIZATION_ID=str(self.org.pk))
        self.assertEqual(foreign.status_code,404,foreign.content)
