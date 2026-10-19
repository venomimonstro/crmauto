import uuid
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from crm.models import Customer, Vehicle
from identity.models import Organization, Branch, Membership, User

@override_settings(BILLING_ENFORCE_WRITES=False)
class BookingContractTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="СТО")
        self.other = Organization.objects.create(name="Чужая СТО")
        self.branch = Branch.objects.create(organization=self.org, name="Основной", code="main")
        self.user = User.objects.create_user("booking@example.invalid", "LongAndUniquePassword999!")
        Membership.objects.create(organization=self.org, user=self.user, role="owner")
        self.c = Customer.objects.create(organization=self.org, name="Владелец")
        self.v = Vehicle.objects.create(organization=self.org, make="Toyota", model="Camry")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.header = {"HTTP_X_ORGANIZATION_ID": str(self.org.id)}
        self.start = timezone.now() + timedelta(days=1)

    def post(self, path, data):
        return self.client.post(path, data, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()), **self.header)

    def bay(self):
        res = self.post("/api/v1/bays", {"branch_id":str(self.branch.id),"name":"Пост 1"})
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()["id"]

    def appointment(self, bay, start=None):
        start = start or self.start
        return self.post("/api/v1/appointments", {
            "branch_id":str(self.branch.id), "customer_id":str(self.c.id),
            "vehicle_id":str(self.v.id), "bay_id":bay,
            "start_at": start.isoformat(), "end_at":(start+timedelta(hours=2)).isoformat(),
        })

    def test_overlap_rejected_and_adjacent_allowed(self):
        bay = self.bay()
        self.assertEqual(self.appointment(bay).status_code, 201)
        self.assertEqual(self.appointment(bay, self.start + timedelta(hours=1)).status_code, 409)
        self.assertEqual(self.appointment(bay, self.start + timedelta(hours=2)).status_code, 201)

    def test_arrival_creates_one_visit(self):
        bay = self.bay()
        pk = self.appointment(bay).json()["id"]
        arrived = self.post(f"/api/v1/appointments/{pk}/arrive", {})
        self.assertEqual(arrived.status_code, 200)
        self.assertIsNotNone(arrived.json()["visit_id"])
        self.assertEqual(self.post(f"/api/v1/appointments/{pk}/arrive", {}).status_code, 409)

    def test_cross_company_client_rejected(self):
        foreign = Customer.objects.create(organization=self.other, name="Чужой")
        bay = self.bay()
        resp = self.post("/api/v1/appointments", {
            "branch_id":str(self.branch.id),"customer_id":str(foreign.id),
            "vehicle_id":str(self.v.id), "bay_id":bay,
            "start_at":self.start.isoformat(),"end_at":(self.start+timedelta(hours=1)).isoformat()
        })
        self.assertEqual(resp.status_code, 404)

    def test_cancel_frees_bay(self):
        bay = self.bay()
        pk = self.appointment(bay).json()["id"]
        self.assertEqual(self.post(f"/api/v1/appointments/{pk}/cancel", {}).status_code, 200)
        self.assertEqual(self.appointment(bay).status_code, 201)
