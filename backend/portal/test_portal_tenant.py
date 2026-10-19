from django.test import TestCase,override_settings
from rest_framework.test import APIClient
from identity.models import Organization,User
@override_settings(BILLING_ENFORCE_WRITES=False)
class PortalTenantSmoke(TestCase):
    def test_unknown_order_never_leaks(self):
        user=User.objects.create_user("portal-example@example.invalid","PassphraseNeverShared357!")
        c=APIClient()
        c.force_authenticate(user)
        response=c.get("/api/v1/portal/orders/00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code,404)
