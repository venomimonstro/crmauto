from django.test import TestCase
from rest_framework.test import APIClient
from identity.models import Organization, Branch, Membership, User

class AnalyticsAccessTests(TestCase):
    def test_anonymous_cannot_read_reports(self):
        response=self.client.get("/api/v1/reports/finance")
        self.assertIn(response.status_code,(401,403))
    def test_foreign_tenant_is_not_visible(self):
        first=Organization.objects.create(name="First")
        foreign=Organization.objects.create(name="Other")
        Branch.objects.create(organization=foreign,name="Main",code="main")
        user=User.objects.create_user("reader@test.invalid","VeryStrongPassword99999")
        Membership.objects.create(organization=first,user=user,role="viewer")
        c=APIClient()
        c.force_authenticate(user)
        response=c.get("/api/v1/reports/finance",HTTP_X_ORGANIZATION_ID=str(foreign.id))
        self.assertEqual(response.status_code,404)
