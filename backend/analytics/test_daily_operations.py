from datetime import timedelta
from uuid import uuid4

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Branch, Membership, Organization, User
from crm.models import Customer, Vehicle
from scheduling.models import Appointment, Visit
from workorders.models import WorkOrder
from inventory.models import Part, Stock, Warehouse, Reservation
from billing.models import Plan, Subscription


@override_settings(BILLING_ENFORCE_WRITES=True)
class DailyOperationsContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="СТО")
        self.other=Organization.objects.create(name="Другая СТО")
        self.branch=Branch.objects.create(organization=self.org,name="Main",code="main")
        self.other_branch=Branch.objects.create(organization=self.other,name="Other",code="main")
        self.owner=User.objects.create_user("ops@test.invalid","SafePassword9292929292!")
        Membership.objects.create(user=self.owner,organization=self.org,role="owner")
        plan=Plan.objects.create(code="ops-test",name="Тест",price_minor=100)
        Subscription.objects.create(organization=self.org,plan=plan,state="active",
            paid_through=timezone.now()+timedelta(days=10))
        self.client=APIClient()
        self.client.force_authenticate(self.owner)

    def daily(self, branch):
        return self.client.get("/api/v1/reports/daily?branch_id="+str(branch.id),
            HTTP_X_ORGANIZATION_ID=str(self.org.id))

    def test_counts_active_workflow(self):
        c=Customer.objects.create(organization=self.org,name="Иван")
        v=Vehicle.objects.create(organization=self.org,make="Toyota",model="Camry")
        now=timezone.now()
        a=Appointment.objects.create(organization=self.org,branch=self.branch,
            customer=c,vehicle=v,start_at=now,end_at=now+timedelta(hours=2),status="arrived")
        Visit.objects.create(organization=self.org,branch=self.branch,
            appointment=a,customer=c,vehicle=v)
        response=self.daily(self.branch)
        self.assertEqual(response.status_code,200,response.content)
        data=response.json()
        self.assertEqual(data["open_visits"],1)
        self.assertEqual(data["workorders_ready"],0)
        self.assertEqual(data["purchases_waiting_receiving"],0)
        self.assertEqual(data["outstanding_minor"],0)

    def test_foreign_branch_does_not_leak(self):
        response=self.daily(self.other_branch)
        self.assertEqual(response.status_code,404,response.content)

    def test_expired_subscription_preserves_read_only_reports(self):
        sub=Subscription.objects.get(organization=self.org)
        sub.paid_through=timezone.now()-timedelta(days=1)
        sub.save(update_fields=["paid_through"])
        response=self.daily(self.branch)
        self.assertEqual(response.status_code,200,response.content)
