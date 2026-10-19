from datetime import timedelta
from uuid import uuid4
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization,Branch,Membership,MemberBranch,User
from crm.models import Customer,Vehicle
from scheduling.models import Appointment,Visit
from workorders.models import WorkOrder,RepairTask

@override_settings(BILLING_ENFORCE_WRITES=False)
class RepairTaskContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="Service")
        self.other=Organization.objects.create(name="Other")
        self.branch=Branch.objects.create(organization=self.org,name="Main",code="main")
        self.owner=User.objects.create_user("owner-task@test.invalid","StrongPassword999992!")
        self.mechanic_user=User.objects.create_user("mechanic-task@test.invalid","StrongPassword999992!")
        self.stranger=User.objects.create_user("stranger-task@test.invalid","StrongPassword999992!")
        Membership.objects.create(organization=self.org,user=self.owner,role="owner")
        self.mechanic=Membership.objects.create(organization=self.org,user=self.mechanic_user,role="mechanic")
        MemberBranch.objects.create(membership=self.mechanic,branch=self.branch)
        customer=Customer.objects.create(organization=self.org,name="Client")
        car=Vehicle.objects.create(organization=self.org,make="VW",model="Golf")
        now=timezone.now()
        ap=Appointment.objects.create(organization=self.org,branch=self.branch,customer=customer,vehicle=car,
            start_at=now,end_at=now+timedelta(hours=2))
        visit=Visit.objects.create(organization=self.org,branch=self.branch,appointment=ap,customer=customer,vehicle=car)
        self.order=WorkOrder.objects.create(organization=self.org,branch=self.branch,visit=visit,
            customer=customer,vehicle=car,created_by=self.owner,status="in_progress")
        self.client=APIClient()
        self.client.force_authenticate(self.owner)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}
    def post(self,path,data=None):
        return self.client.post("/api/v1/"+path,data or {},format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.headers)
    def test_task_lifecycle_and_qa_gate(self):
        created=self.post(f"workorders/{self.order.pk}/tasks",{
            "membership_id":str(self.mechanic.pk),"title":"Замена деталей"})
        self.assertEqual(created.status_code,201,created.content)
        pk=created.json()["id"]
        blocked=self.post(f"workorders/{self.order.pk}/actions/qa")
        self.assertEqual(blocked.status_code,409,blocked.content)
        self.client.force_authenticate(self.mechanic_user)
        started=self.post(f"workorders/{self.order.pk}/tasks/{pk}/start")
        self.assertEqual(started.status_code,200,started.content)
        self.assertIsNotNone(started.json()["started_at"])
        finished=self.post(f"workorders/{self.order.pk}/tasks/{pk}/finish")
        self.assertEqual(finished.status_code,200,finished.content)
        self.assertIsNotNone(finished.json()["completed_at"])
        self.assertEqual(self.post(f"workorders/{self.order.pk}/tasks/{pk}/finish").status_code,409)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.post(f"workorders/{self.order.pk}/actions/qa").status_code,200)
    def test_cannot_run_two_tasks_at_once(self):
        ids=[]
        for title in ("Job A","Job B"):
            created=self.post(f"workorders/{self.order.pk}/tasks",{
                "membership_id":str(self.mechanic.pk),"title":title})
            self.assertEqual(created.status_code,201,created.content);ids.append(created.json()["id"])
        self.client.force_authenticate(self.mechanic_user)
        self.assertEqual(self.post(f"workorders/{self.order.pk}/tasks/{ids[0]}/start").status_code,200)
        self.assertEqual(self.post(f"workorders/{self.order.pk}/tasks/{ids[1]}/start").status_code,409)
        self.assertEqual(RepairTask.objects.filter(state="running").count(),1)
    def test_unrelated_user_cannot_read_tasks(self):
        self.client.force_authenticate(self.stranger)
        self.assertEqual(self.client.get(f"/api/v1/workorders/{self.order.pk}/tasks",
            **self.headers).status_code,404)
