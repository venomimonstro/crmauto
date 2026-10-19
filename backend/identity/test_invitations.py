from datetime import timedelta
from urllib.parse import urlparse, parse_qs
from uuid import uuid4

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from billing.models import Plan, Subscription
from identity.models import (Branch, MemberBranch, Membership,
                             Organization, StaffInvitation, User)


@override_settings(
    BILLING_ENFORCE_WRITES=True,
    ENABLE_EMAIL_ONBOARDING=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PUBLIC_WEB_ORIGIN="https://crm.example.invalid",
    DEFAULT_FROM_EMAIL="noreply@example.invalid",
)
class StaffInvitationJourney(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner-invite@test.invalid", "SafeLongPassword887766!")
        self.new_staff = User.objects.create_user("worker-invite@test.invalid", "SafeLongPassword887766!")
        self.stranger = User.objects.create_user("stranger-invite@test.invalid", "SafeLongPassword887766!")
        self.org = Organization.objects.create(name="Service")
        self.branch = Branch.objects.create(organization=self.org, name="Main", code="main")
        Membership.objects.create(organization=self.org, user=self.owner, role="owner")
        plan = Plan.objects.create(code="invite-test", name="Test", price_minor=10000,
                                   max_staff=2, max_branches=1)
        Subscription.objects.create(organization=self.org, plan=plan, state="active",
                                    paid_through=timezone.now()+timedelta(days=7))
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.headers = {"HTTP_X_ORGANIZATION_ID": str(self.org.id)}

    def send_invite(self):
        return self.client.post("/api/v1/staff/invitations",
            {"email": self.new_staff.email, "role": "mechanic", "branch_id": str(self.branch.id)},
            HTTP_IDEMPOTENCY_KEY=str(uuid4()),format="json",**self.headers)

    def token_from_mail(self):
        self.assertEqual(len(mail.outbox), 1)
        link = next(word for word in mail.outbox[0].body.split()
                    if word.startswith("https://"))
        return parse_qs(urlparse(link).query)["staff_invite"][0]

    def test_owner_invites_and_staff_accepts_exactly_once(self):
        created=self.send_invite()
        self.assertEqual(created.status_code,201,created.content)
        token=self.token_from_mail()
        self.client.force_authenticate(self.new_staff)
        accepted=self.client.post("/api/v1/staff/invitations/accept",
                                  {"token": token},format="json")
        self.assertEqual(accepted.status_code,201,accepted.content)
        self.assertEqual(accepted.json()["role"],"mechanic")
        member=Membership.objects.get(organization=self.org,user=self.new_staff)
        self.assertTrue(MemberBranch.objects.filter(membership=member,branch=self.branch).exists())
        retry=self.client.post("/api/v1/staff/invitations/accept",{"token":token},format="json")
        self.assertEqual(retry.status_code,409,retry.content)
        self.assertEqual(Membership.objects.filter(organization=self.org).count(),2)

    def test_stolen_link_cannot_add_uninvited_account(self):
        self.assertEqual(self.send_invite().status_code,201)
        token=self.token_from_mail()
        self.client.force_authenticate(self.stranger)
        response=self.client.post("/api/v1/staff/invitations/accept",
                                  {"token":token},format="json")
        self.assertEqual(response.status_code,403,response.content)
        self.assertFalse(Membership.objects.filter(user=self.stranger,organization=self.org).exists())

    def test_pending_seat_uses_plan_limit(self):
        self.assertEqual(self.send_invite().status_code,201)
        # Owner + invitation already fill the 2 seats.
        response=self.client.post("/api/v1/staff/invitations",
          {"email":"third@test.invalid","role":"mechanic","branch_id":str(self.branch.id)},
          HTTP_IDEMPOTENCY_KEY=str(uuid4()),format="json",**self.headers)
        self.assertEqual(response.status_code,409,response.content)
        self.assertEqual(StaffInvitation.objects.filter(organization=self.org).count(),1)

    def test_expired_subscription_blocks_invitation(self):
        sub=Subscription.objects.get(organization=self.org)
        sub.paid_through=timezone.now()-timedelta(days=1)
        sub.save(update_fields=["paid_through"])
        response=self.send_invite()
        self.assertEqual(response.status_code,403,response.content)
        self.assertFalse(StaffInvitation.objects.exists())

    def test_manager_cannot_issue_manager_role(self):
        manager=User.objects.create_user("manager-invite@test.invalid","SafeLongPassword887766!")
        member=Membership.objects.create(organization=self.org,user=manager,role="manager")
        self.client.force_authenticate(manager)
        response=self.client.post("/api/v1/staff/invitations",
          {"email":"third@test.invalid","role":"manager"},
          HTTP_IDEMPOTENCY_KEY=str(uuid4()),format="json",**self.headers)
        self.assertEqual(response.status_code,403,response.content)
