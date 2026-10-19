from datetime import timedelta
from uuid import uuid4
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization,Branch,Membership,User
from crm.models import Customer,Vehicle
from scheduling.models import Appointment,Visit
from workorders.models import WorkOrder,AdditionalWork

@override_settings(BILLING_ENFORCE_WRITES=False)
class AdditionalWorkContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="Main")
        self.foreign=Organization.objects.create(name="Foreign")
        self.branch=Branch.objects.create(organization=self.org,name="Main",code="main")
        user=User.objects.create_user("additional@test.invalid","CorrectLongPassword779911!")
        Membership.objects.create(organization=self.org,user=user,role="owner")
        c=Customer.objects.create(organization=self.org,name="Client")
        car=Vehicle.objects.create(organization=self.org,make="Toyota",model="Camry")
        now=timezone.now()
        ap=Appointment.objects.create(organization=self.org,branch=self.branch,customer=c,vehicle=car,start_at=now,end_at=now+timedelta(hours=1))
        visit=Visit.objects.create(organization=self.org,branch=self.branch,customer=c,vehicle=car,appointment=ap)
        self.order=WorkOrder.objects.create(organization=self.org,branch=self.branch,customer=c,vehicle=car,visit=visit,created_by=user,status="in_progress")
        self.client=APIClient();self.client.force_authenticate(user)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}
    def post(self,path,data):
        return self.client.post("/api/v1/"+path,data,format="json",HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.headers)
    def test_new_defect_recorded_without_approval_or_invoice(self):
        result=self.post(f"workorders/{self.order.pk}/additional-works",{
            "title":"Additional work","description":"Customer must approve before work",
            "amount_minor":100000})
        self.assertEqual(result.status_code,201,result.content)
        pk=result.json()["id"]
        self.assertEqual(result.json()["status"],"proposed")
        approval=self.post(f"workorders/{self.order.pk}/additional-works/{pk}/approve",{
            "reference":"Employee said yes"})
        self.assertEqual(approval.status_code,400,approval.content)
        self.assertEqual(AdditionalWork.objects.get(pk=pk).status,"proposed")
        declined=self.post(f"workorders/{self.order.pk}/additional-works/{pk}/decline",{})
        self.assertEqual(declined.status_code,200,declined.content)
    def test_foreign_tenant_cannot_read_findings(self):
        result=self.client.get(f"/api/v1/workorders/{uuid4()}/additional-works",
            **self.headers)
        self.assertEqual(result.status_code,404,result.content)
    def test_cannot_propose_after_ready(self):
        self.order.status="ready";self.order.save(update_fields=["status"])
        result=self.post(f"workorders/{self.order.pk}/additional-works",{
            "title":"More","description":"Late","amount_minor":100})
        self.assertEqual(result.status_code,409,result.content)

    def test_unresolved_additional_work_blocks_quality_check(self):
        proposal=self.post(f"workorders/{self.order.pk}/additional-works",{
            "title":"Повреждение тормозного шланга",
            "description":"Требуется согласование клиента",
            "amount_minor":45000})
        self.assertEqual(proposal.status_code,201,proposal.content)
        blocked=self.post(f"workorders/{self.order.pk}/actions/qa",{})
        self.assertEqual(blocked.status_code,409,blocked.content)
        self.assertEqual(WorkOrder.objects.get(pk=self.order.pk).status,"in_progress")
        declined=self.post(f"workorders/{self.order.pk}/additional-works/{proposal.json()['id']}/decline",{})
        self.assertEqual(declined.status_code,200,declined.content)
        allowed=self.post(f"workorders/{self.order.pk}/actions/qa",{})
        self.assertEqual(allowed.status_code,200,allowed.content)
