from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from identity.models import Branch, MemberBranch, Membership, Organization, User
from identity.scope import resolve_scope
from rest_framework.exceptions import NotFound, PermissionDenied


@override_settings(BILLING_ENFORCE_WRITES=False)
class TenantIsolationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@test.invalid", "CorrectHorseBattery999!")
        self.staff = User.objects.create_user("worker@test.invalid", "CorrectHorseBattery999!")
        self.a = Organization.objects.create(name="A")
        self.b = Organization.objects.create(name="B")
        self.branch_a = Branch.objects.create(organization=self.a, name="A main", code="a")
        self.branch_b = Branch.objects.create(organization=self.b, name="B main", code="b")
        self.owner_a = Membership.objects.create(organization=self.a, user=self.owner, role="owner")
        self.member_a = Membership.objects.create(organization=self.a, user=self.staff, role="mechanic")
        MemberBranch.objects.create(membership=self.member_a, branch=self.branch_a)

    def test_cross_tenant_scope_is_404(self):
        c = APIClient()
        c.force_authenticate(self.owner)
        response = c.get("/api/v1/branches", HTTP_X_ORGANIZATION_ID=str(self.b.id))
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_branch_not_found(self):
        c = APIClient()
        c.force_authenticate(self.staff)
        response = c.get("/api/v1/branches", HTTP_X_ORGANIZATION_ID=str(self.a.id),
                         HTTP_X_BRANCH_ID=str(self.branch_b.id))
        self.assertEqual(response.status_code, 404)

    def test_owner_can_create_branch_only_in_own_tenant(self):
        c = APIClient()
        c.force_authenticate(self.owner)
        response = c.post("/api/v1/branches", {"name": "Second", "code": "second"},
                          format="json", HTTP_X_ORGANIZATION_ID=str(self.a.id))
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Branch.objects.filter(organization=self.a, code="second").exists())

    def test_staff_cannot_create_branch(self):
        c = APIClient()
        c.force_authenticate(self.staff)
        response = c.post("/api/v1/branches", {"name": "Fake", "code": "fake"},
                          format="json", HTTP_X_ORGANIZATION_ID=str(self.a.id))
        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_grant_rejected(self):
        with self.assertRaises(Exception):
            MemberBranch.objects.create(membership=self.member_a, branch=self.branch_b)

    def test_anonymous_is_not_organization_member(self):
        response = self.client.get("/api/v1/organizations")
        self.assertIn(response.status_code, (401, 403))
