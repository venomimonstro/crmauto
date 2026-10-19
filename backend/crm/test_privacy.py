from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from identity.models import Organization, Branch, User, Membership, MemberBranch
from crm.models import Customer, Vehicle, Ownership

@override_settings(BILLING_ENFORCE_WRITES=False)
class TenantSearchPrivacyTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="Privacy")
        self.branch=Branch.objects.create(organization=self.org,code="main",name="Main")
        self.customer=Customer.objects.create(organization=self.org,name="Private owner")
        self.vehicle=Vehicle.objects.create(organization=self.org,make="BMW",model="320i")
        Ownership.objects.create(organization=self.org,customer=self.customer,vehicle=self.vehicle)
        self.mechanic=User.objects.create_user("mechanic@test.invalid","SafePassword8899001!")
        self.cashier=User.objects.create_user("cashier@test.invalid","SafePassword8899001!")
        m=Membership.objects.create(user=self.mechanic,organization=self.org,role="mechanic")
        MemberBranch.objects.create(membership=m,branch=self.branch)
        Membership.objects.create(user=self.cashier,organization=self.org,role="cashier")
        self.client=APIClient()
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}

    def test_mechanic_can_find_vehicle_without_owner_identity(self):
        self.client.force_authenticate(self.mechanic)
        result=self.client.get("/api/v1/vehicles",**self.headers)
        self.assertEqual(result.status_code,200,result.content)
        self.assertEqual(len(result.json()),1)
        self.assertNotIn("current_owner",result.json()[0])
        detail=self.client.get("/api/v1/vehicles/"+str(self.vehicle.id),**self.headers)
        self.assertEqual(detail.status_code,200,detail.content)
        self.assertNotIn("current_owner",detail.json())
        search=self.client.get("/api/v1/search?q=BMW",**self.headers)
        self.assertEqual(search.status_code,200,search.content)
        self.assertEqual(search.json()["customers"],[])
        self.assertNotIn("current_owner",search.json()["vehicles"][0])

    def test_cashier_cannot_search_vehicle_register(self):
        self.client.force_authenticate(self.cashier)
        search=self.client.get("/api/v1/search?q=BMW",**self.headers)
        self.assertEqual(search.status_code,403,search.content)
        vehicles=self.client.get("/api/v1/vehicles",**self.headers)
        self.assertEqual(vehicles.status_code,403,vehicles.content)
