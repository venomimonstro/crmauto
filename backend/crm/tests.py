import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from identity.models import Membership, Organization, User
from crm.models import Customer, Ownership

class CRMContracts(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("main@example.invalid", "CorrectHorseBattery999!")
        self.other = User.objects.create_user("other@example.invalid", "CorrectHorseBattery999!")
        self.company = Organization.objects.create(name="Our service")
        self.foreign = Organization.objects.create(name="Other service")
        Membership.objects.create(organization=self.company, user=self.user, role="owner")
        Membership.objects.create(organization=self.foreign, user=self.other, role="owner")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.org_header = {"HTTP_X_ORGANIZATION_ID": str(self.company.pk)}

    def post(self, path, data, key=None):
        return self.client.post(path, data, format="json",
                                HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()), **self.org_header)

    def test_repeat_command_same_effect(self):
        key = str(uuid.uuid4())
        data = {"name": "Иван Иванов", "phone": "+7 (999) 123-45-67"}
        first = self.post("/api/v1/customers", data, key)
        repeat = self.post("/api/v1/customers", data, key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(repeat.json(), first.json())
        self.assertEqual(Customer.objects.filter(organization=self.company).count(), 1)

    def test_conflicting_payload_same_key(self):
        key = str(uuid.uuid4())
        self.post("/api/v1/customers", {"name": "Алексей"}, key)
        bad = self.post("/api/v1/customers", {"name": "Василий"}, key)
        self.assertEqual(bad.status_code, 409)

    def test_no_foreign_owner_links(self):
        foreign_customer = Customer.objects.create(organization=self.foreign, name="Чужой")
        response = self.post("/api/v1/vehicles", {"make": "BMW", "model": "X5",
                                                   "owner_id": str(foreign_customer.pk)})
        self.assertEqual(response.status_code, 404)

    def test_transfer_keeps_history(self):
        a = self.post("/api/v1/customers", {"name": "Первый"}).json()["id"]
        b = self.post("/api/v1/customers", {"name": "Второй"}).json()["id"]
        car = self.post("/api/v1/vehicles", {"make": "BMW", "model": "X5", "owner_id": a}).json()
        moved = self.post(f'/api/v1/vehicles/{car["id"]}/transfer', {"customer_id": b})
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(Ownership.objects.filter(vehicle_id=car["id"]).count(), 2)
        self.assertEqual(Ownership.objects.filter(vehicle_id=car["id"], ended_on__isnull=True).count(), 1)

    def test_optimistic_lock_conflicts(self):
        id = self.post("/api/v1/customers", {"name": "Антон"}).json()["id"]
        updated = self.client.patch(f"/api/v1/customers/{id}", {"name": "Антон П."},
                                    format="json", HTTP_IF_MATCH="1", **self.org_header)
        self.assertEqual(updated.status_code, 200)
        again = self.client.patch(f"/api/v1/customers/{id}", {"name": "Антон М."},
                                  format="json", HTTP_IF_MATCH="1", **self.org_header)
        self.assertEqual(again.status_code, 409)
