from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization, Membership, User
from billing.models import Plan, Subscription

class SubscriptionStatusTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="Shop")
        self.user=User.objects.create_user("owner@example.invalid","StrongTestPassword992288")
        Membership.objects.create(organization=self.org,user=self.user,role="owner")
        self.client=APIClient()
        self.client.force_authenticate(self.user)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}
        self.plan=Plan.objects.create(code="base",name="Base",price_minor=100000)

    def status(self):
        return self.client.get("/api/v1/billing/subscription",**self.headers)

    def test_missing_subscription_is_restricted(self):
        self.assertEqual(self.status().json()["access"],"restricted")

    def test_expired_trial_is_read_only(self):
        Subscription.objects.create(organization=self.org,plan=self.plan,state="trial",
            trial_ends_at=timezone.now()-timedelta(days=1))
        self.assertEqual(self.status().json()["access"],"read_only")

    def test_active_current_subscription_is_write_capable_status(self):
        Subscription.objects.create(organization=self.org,plan=self.plan,state="active",
            paid_through=timezone.now()+timedelta(days=10))
        self.assertEqual(self.status().json()["access"],"write")
