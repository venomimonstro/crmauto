from uuid import uuid4
from django.test import TestCase,override_settings
from rest_framework.test import APIClient
from identity.models import Organization,Membership,User,ServicePolicy

@override_settings(BILLING_ENFORCE_WRITES=False)
class ServicePolicyContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="Сервис")
        self.other=Organization.objects.create(name="Конкурент")
        self.owner=User.objects.create_user("terms-owner@example.invalid","StrongPassword712478!")
        self.viewer=User.objects.create_user("terms-viewer@example.invalid","StrongPassword712478!")
        Membership.objects.create(organization=self.org,user=self.owner,role="owner")
        Membership.objects.create(organization=self.org,user=self.viewer,role="viewer")
        self.client=APIClient()
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.pk)}
    def publish(self,service):
        return self.client.post("/api/v1/organization/service-policies",{
            "service_terms":service,"warranty_terms":"Порядок гарантийного обслуживания устанавливается договором."},
            format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.headers)
    def test_revision_history_and_duplicate_rejection(self):
        self.client.force_authenticate(self.owner)
        first=self.publish("Первая редакция условий обслуживания автосервиса.")
        self.assertEqual(first.status_code,201,first.content)
        second=self.publish("Вторая редакция условий обслуживания автосервиса.")
        self.assertEqual(second.status_code,201,second.content)
        self.assertEqual(second.json()["version"],2)
        self.assertEqual(ServicePolicy.objects.filter(organization=self.org,is_current=True).count(),1)
        self.assertEqual(self.publish("Вторая редакция условий обслуживания автосервиса.").status_code,409)
        rows=self.client.get("/api/v1/organization/service-policies",**self.headers).json()
        self.assertEqual([x["version"] for x in rows],[2,1])
    def test_viewer_cannot_publish_or_read_foreign_tenant(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.publish("Попытка изменить чужие условия обслуживания.").status_code,403)
        self.assertEqual(self.client.get("/api/v1/organization/service-policies",
            HTTP_X_ORGANIZATION_ID=str(self.other.pk)).status_code,404)
