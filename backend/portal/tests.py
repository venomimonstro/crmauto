from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization, Branch, User
from crm.models import Customer, Vehicle, Ownership
from scheduling.models import Appointment, Visit
from workorders.models import WorkOrder
from .models import PortalGrant

class PortalSecurityTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="Shop")
        self.other=Organization.objects.create(name="Other")
        self.branch=Branch.objects.create(organization=self.org,name="Main",code="main")
        self.user=User.objects.create_user("driver@test.invalid","LongPassword88553221!")
        self.staff=User.objects.create_user("staff@test.invalid","LongPassword88553222!")
        self.customer=Customer.objects.create(organization=self.org,name="Customer")
        self.foreign=Customer.objects.create(organization=self.other,name="Foreign")
        self.vehicle=Vehicle.objects.create(organization=self.org,make="Ford",model="Focus")
        Ownership.objects.create(organization=self.org,vehicle=self.vehicle,customer=self.customer)
        self.client=APIClient()
        self.client.force_authenticate(self.user)

    def test_inactive_grant_has_no_access(self):
        PortalGrant.objects.create(organization=self.org,customer=self.customer,
            user=self.user,verified_by=self.staff,verification_reference="Internal test",active=False)
        self.assertEqual(self.client.get("/api/v1/portal/me").json()["accounts"],[])

    def test_active_grant_sees_only_own_vehicle(self):
        PortalGrant.objects.create(organization=self.org,customer=self.customer,
            user=self.user,verified_by=self.staff,verification_reference="Internal test",active=True)
        response=self.client.get("/api/v1/portal/me")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json()["accounts"]),1)
        self.assertEqual(len(response.json()["accounts"][0]["vehicles"]),1)

    def test_guessed_foreign_order_is_not_visible(self):
        now=timezone.now()
        branch=Branch.objects.create(organization=self.other,name="Branch",code="foreign")
        car=Vehicle.objects.create(organization=self.other,make="VW",model="Golf")
        appointment=Appointment.objects.create(organization=self.other,branch=branch,
            customer=self.foreign,vehicle=car,start_at=now,end_at=now+timedelta(hours=1))
        visit=Visit.objects.create(organization=self.other,branch=branch,
            appointment=appointment,customer=self.foreign,vehicle=car)
        order=WorkOrder.objects.create(organization=self.other,branch=branch,
            visit=visit,customer=self.foreign,vehicle=car,created_by=self.staff)
        PortalGrant.objects.create(organization=self.org,customer=self.customer,
            user=self.user,verified_by=self.staff,verification_reference="Internal test",active=True)
        self.assertEqual(self.client.get(f"/api/v1/portal/orders/{order.id}").status_code,404)
