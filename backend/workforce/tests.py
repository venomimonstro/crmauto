import uuid
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Organization,Branch,Membership,User
from crm.models import Customer,Vehicle,Ownership
from workforce.models import TireSet,Shift

@override_settings(BILLING_ENFORCE_WRITES=False)
class WorkforceContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="A")
        self.branch=Branch.objects.create(organization=self.org,name="Main",code="main")
        self.user=User.objects.create_user("manager@test.invalid","LongTestPassword446688!")
        self.member=Membership.objects.create(organization=self.org,user=self.user,role="manager")
        self.customer=Customer.objects.create(organization=self.org,name="Клиент")
        self.client=APIClient()
        self.client.force_authenticate(self.user)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}
    def post(self,path,data,key=None):
        return self.client.post("/api/v1/"+path,data,format="json",
            HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),**self.headers)
    def test_tires_are_not_inventory_stock(self):
        request={"branch_id":str(self.branch.id),"customer_id":str(self.customer.id),
                 "code":"TYRE-01","pieces":4,"description":"Зимние колёса","storage_location":"A-1"}
        result=self.post("tire-sets",request)
        self.assertEqual(result.status_code,201,result.content)
        from inventory.models import Stock
        self.assertEqual(Stock.objects.count(),0)
        pk=result.json()["id"]
        self.assertEqual(self.post(f"tire-sets/{pk}/release",{}).status_code,200)
        self.assertEqual(self.post(f"tire-sets/{pk}/release",{}).status_code,409)
    def test_overlap_shift_rejected(self):
        start=timezone.now()
        data={"branch_id":str(self.branch.id),"membership_id":str(self.member.id),
            "begins":start.isoformat(),"ends":(start+timedelta(hours=8)).isoformat()}
        self.assertEqual(self.post("staff-shifts",data).status_code,201)
        self.assertEqual(self.post("staff-shifts",data).status_code,409)
        self.assertEqual(Shift.objects.count(),1)

    def test_cannot_store_customer_tires_against_another_owners_vehicle(self):
        other=Customer.objects.create(organization=self.org,name="Другой клиент")
        car=Vehicle.objects.create(organization=self.org,make="VW",model="Polo")
        Ownership.objects.create(organization=self.org,vehicle=car,customer=other)
        request={"branch_id":str(self.branch.id),"customer_id":str(self.customer.id),
                 "vehicle_id":str(car.id),"code":"TYRE-OTHER",
                 "pieces":4,"description":"Чужой комплект","storage_location":"A-2"}
        result=self.post("tire-sets",request)
        self.assertEqual(result.status_code,409,result.content)
        self.assertEqual(TireSet.objects.count(),0)
        request["customer_id"]=str(other.id)
        valid=self.post("tire-sets",request)
        self.assertEqual(valid.status_code,201,valid.content)
        self.assertEqual(TireSet.objects.count(),1)
