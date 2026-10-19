from django.test import SimpleTestCase
from django.urls import reverse


class HealthTests(SimpleTestCase):
    def test_live_is_public(self):
        response = self.client.get(reverse("live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_health_not_mutable(self):
        self.assertEqual(self.client.post(reverse("live")).status_code, 405)
