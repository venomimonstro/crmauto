from datetime import timedelta
from uuid import uuid4
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization,Branch,Membership,User,OrganizationLegalProfile
from crm.models import Customer,Vehicle
from scheduling.models import Appointment,Visit
from workorders.models import WorkOrder

@override_settings(BILLING_ENFORCE_WRITES=False)
class LegalProfileDocumentsTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="СТО 1")
        self.other=Organization.objects.create(name="СТО 2")
        self.owner=User.objects.create_user("legal@invalid.test","LongPassword448800!")
        Membership.objects.create(organization=self.org,user=self.owner,role="owner")
        self.client=APIClient();self.client.force_authenticate(self.owner)
        self.h={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}
    def test_create_update_and_optimistic_lock(self):
        initial=self.client.get("/api/v1/organization/legal-profile",**self.h)
        self.assertEqual(initial.status_code,200,initial.content)
        changed=self.client.patch("/api/v1/organization/legal-profile",{
            "legal_name":"ООО Сервис","inn":"7701234567","service_address":"Москва"},
            format="json",HTTP_IF_MATCH="1",HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.h)
        self.assertEqual(changed.status_code,200,changed.content)
        self.assertEqual(changed.json()["version"],2)
        stale=self.client.patch("/api/v1/organization/legal-profile",{
            "legal_name":"Устаревшие данные"},format="json",
            HTTP_IF_MATCH="1",HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.h)
        self.assertEqual(stale.status_code,409,stale.content)
        self.assertEqual(OrganizationLegalProfile.objects.get(organization=self.org).legal_name,"ООО Сервис")
    def test_cross_tenant_profile_not_accessible(self):
        foreign=self.client.get("/api/v1/organization/legal-profile",
            HTTP_X_ORGANIZATION_ID=str(self.other.id))
        self.assertEqual(foreign.status_code,404,foreign.content)
    def test_profile_in_order_printout(self):
        OrganizationLegalProfile.objects.create(organization=self.org,legal_name="ООО Сервис",
            inn="7701234567",service_address="г. Москва")
        b=Branch.objects.create(organization=self.org,name="Филиал",code="one")
        c=Customer.objects.create(organization=self.org,name="Иван")
        v=Vehicle.objects.create(organization=self.org,make="Kia",model="Rio")
        start=timezone.now()
        a=Appointment.objects.create(organization=self.org,branch=b,customer=c,vehicle=v,
            start_at=start,end_at=start+timedelta(hours=1))
        visit=Visit.objects.create(organization=self.org,branch=b,appointment=a,customer=c,vehicle=v)
        order=WorkOrder.objects.create(organization=self.org,branch=b,visit=visit,
            customer=c,vehicle=v,created_by=self.owner)
        result=self.client.post(f"/api/v1/workorders/{order.id}/documents",{"type":"work_order"},
            format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.h)
        self.assertEqual(result.status_code,201,result.content)
        detail=self.client.get(f"/api/v1/workorders/{order.id}/documents/{result.json()['id']}",**self.h)
        self.assertIn("7701234567",detail.json()["html"])
        self.assertIn("ООО Сервис",detail.json()["html"])

    def test_rejects_incorrect_identifiers(self):
        original=self.client.get("/api/v1/organization/legal-profile",**self.h)
        self.assertEqual(original.status_code,200,original.content)
        result=self.client.patch("/api/v1/organization/legal-profile",{
            "entity_kind":"company","inn":"123","bik":"12AB56789"},
            format="json",HTTP_IF_MATCH="1",HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.h)
        self.assertEqual(result.status_code,400,result.content)
        profile=OrganizationLegalProfile.objects.get(organization=self.org)
        self.assertEqual(profile.version,1)
        self.assertEqual(profile.inn,"")
