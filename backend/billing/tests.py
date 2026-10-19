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

from django.test import override_settings


class SaaSWriteGateTests(SubscriptionStatusTests):
    def branch_post(self):
        return self.client.post("/api/v1/branches",{"name":"New","code":"new"},
            format="json",**self.headers)

    @override_settings(BILLING_ENFORCE_WRITES=True)
    def test_missing_subscription_blocks_mutation(self):
        response=self.branch_post()
        self.assertEqual(response.status_code,403,response.content)

    @override_settings(BILLING_ENFORCE_WRITES=True)
    def test_expired_subscription_blocks_mutation(self):
        Subscription.objects.create(organization=self.org,plan=self.plan,state="active",
            paid_through=timezone.now()-timedelta(minutes=1))
        response=self.branch_post()
        self.assertEqual(response.status_code,403,response.content)

    @override_settings(BILLING_ENFORCE_WRITES=True)
    def test_current_subscription_allows_mutation(self):
        Subscription.objects.create(organization=self.org,plan=self.plan,state="active",
            paid_through=timezone.now()+timedelta(days=10))
        response=self.branch_post()
        self.assertEqual(response.status_code,201,response.content)

    @override_settings(BILLING_ENFORCE_WRITES=True)
    def test_trial_expired_blocks_mutation(self):
        Subscription.objects.create(organization=self.org,plan=self.plan,state="trial",
            trial_ends_at=timezone.now()-timedelta(minutes=1))
        self.assertEqual(self.branch_post().status_code,403)

@override_settings(BILLING_ENFORCE_WRITES=True)
class SaaSBuyerJourneyTests(TestCase):
    def test_new_organization_trial_and_write_expiration(self):
        buyer=User.objects.create_user("buyer@trial.invalid","LongSafePassword009988!")
        client=APIClient()
        client.force_authenticate(buyer)
        created=client.post("/api/v1/organizations",{"name":"Покупатель тестирует СТО"},format="json")
        self.assertEqual(created.status_code,201,created.content)
        organization_id=created.json()["id"]
        sub=Subscription.objects.get(organization_id=organization_id)
        self.assertEqual(sub.state,"trial")
        self.assertIsNotNone(sub.trial_ends_at)
        headers={"HTTP_X_ORGANIZATION_ID":organization_id}
        customer=client.post("/api/v1/customers",{"name":"Автовладелец"},format="json",
            HTTP_IDEMPOTENCY_KEY=__import__("uuid").uuid4().hex,**headers)
        self.assertEqual(customer.status_code,201,customer.content)
        # The starter plan grants one branch only; the initial branch was provisioned.
        second_branch=client.post("/api/v1/branches",{"name":"Ещё одна","code":"second"},
                                  format="json",**headers)
        self.assertEqual(second_branch.status_code,409,second_branch.content)
        # When trial expires, already stored data remains readable.
        sub.trial_ends_at=timezone.now()-timedelta(seconds=1)
        sub.save(update_fields=["trial_ends_at"])
        read=client.get("/api/v1/customers",**headers)
        self.assertEqual(read.status_code,200,read.content)
        write=client.post("/api/v1/customers",{"name":"Новое лицо"},format="json",
            HTTP_IDEMPOTENCY_KEY=__import__("uuid").uuid4().hex,**headers)
        self.assertEqual(write.status_code,403,write.content)
        self.assertEqual(Subscription.objects.filter(organization_id=organization_id).count(),1)

    def test_repeat_free_trial_organization_is_rejected(self):
        buyer=User.objects.create_user("repeat@trial.invalid","LongSafePassword009988!")
        client=APIClient()
        client.force_authenticate(buyer)
        first=client.post("/api/v1/organizations",{"name":"Первый сервис"},format="json")
        self.assertEqual(first.status_code,201,first.content)
        second=client.post("/api/v1/organizations",{"name":"Второй сервис"},format="json")
        self.assertEqual(second.status_code,400,second.content)
