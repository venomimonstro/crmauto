from datetime import timedelta
from uuid import uuid4
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization,Branch,Membership,User,ServicePolicy
from crm.models import Customer,Vehicle
from scheduling.models import Appointment,Visit
from workorders.models import WorkOrder,OrderDocument

@override_settings(BILLING_ENFORCE_WRITES=False)
class ServicePoliciesContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="СТО")
        self.owner=User.objects.create_user("policy@invalid.test","LongPassword998877!")
        Membership.objects.create(organization=self.org,user=self.owner,role="owner")
        self.client=APIClient();self.client.force_authenticate(self.owner)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.pk)}
    def post(self,service,warranty):
        return self.client.post("/api/v1/organization/service-policies",
            {"service_terms":service,"warranty_terms":warranty},
            format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.headers)
    def test_policy_history_preserves_previous_content(self):
        first=self.post("Первоначальные условия обслуживания по заказ-наряду в мастерской.",
                        "Гарантийные условия по работам определяются письменно.")
        self.assertEqual(first.status_code,201,first.content)
        second=self.post("Изменённые условия обслуживания по заказ-наряду и работам.",
                         "Новая редакция гарантийных обязательств исполнителя.")
        self.assertEqual(second.status_code,201,second.content)
        self.assertEqual(ServicePolicy.objects.filter(organization=self.org,is_current=True).count(),1)
        self.assertEqual(ServicePolicy.objects.get(organization=self.org,version=1).service_terms,
                         "Первоначальные условия обслуживания по заказ-наряду в мастерской.")
    def test_blank_policy_and_duplicate_rejected(self):
        self.assertEqual(self.post("коротко","коротко").status_code,400)
        text="Подробные условия обслуживания и гарантии данного сервиса."
        self.assertEqual(self.post(text,text).status_code,201)
        self.assertEqual(self.post(text,text).status_code,409)
    def test_foreign_tenant_cannot_read_policy(self):
        self.assertEqual(self.client.get("/api/v1/organization/service-policies",
            HTTP_X_ORGANIZATION_ID=str(uuid4())).status_code,404)
