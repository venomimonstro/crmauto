from django.test import SimpleTestCase
from django.urls import reverse


class HealthTests(SimpleTestCase):
    def test_live_is_public(self):
        response = self.client.get(reverse("live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_health_not_mutable(self):
        self.assertEqual(self.client.post(reverse("live")).status_code, 405)

from django.test import TestCase
from rest_framework.test import APIClient
from identity.models import Organization, Membership, User
from crm.models import Customer


class IdempotencyIsolationTests(TestCase):
    def test_receipt_from_another_user_is_not_returned(self):
        org=Organization.objects.create(name="Service")
        first=User.objects.create_user("first@invalid.test","SafePassword9922288!")
        second=User.objects.create_user("second@invalid.test","SafePassword9922288!")
        Membership.objects.create(organization=org,user=first,role="owner")
        Membership.objects.create(organization=org,user=second,role="manager")
        import uuid
        key=str(uuid.uuid4())
        c=APIClient()
        c.force_authenticate(first)
        headers={"HTTP_X_ORGANIZATION_ID":str(org.id),"HTTP_IDEMPOTENCY_KEY":key}
        result=c.post("/api/v1/customers",{"name":"Customer One"},format="json",**headers)
        self.assertEqual(result.status_code,201,result.content)
        c.force_authenticate(second)
        attempt=c.post("/api/v1/customers",{"name":"Customer One"},format="json",**headers)
        self.assertEqual(attempt.status_code,409,attempt.content)
        self.assertNotIn(str(Customer.objects.get().id),str(attempt.content))
        self.assertEqual(Customer.objects.count(),1)
