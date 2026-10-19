import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from identity.models import Organization,Branch,Membership,User
from inventory.models import Warehouse
from dismantling.models import SalvagedPart

class DismantlingContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="Сервис")
        self.other=Organization.objects.create(name="Чужой сервис")
        self.branch=Branch.objects.create(organization=self.org,name="Основной",code="main")
        self.warehouse=Warehouse.objects.create(organization=self.org,branch=self.branch,name="Склад")
        self.user=User.objects.create_user("dismantler@test.invalid","SafePassword449922!!")
        Membership.objects.create(organization=self.org,user=self.user,role="owner")
        self.client=APIClient()
        self.client.force_authenticate(self.user)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}

    def post(self,path,data,key=None):
        return self.client.post("/api/v1/"+path,data,format="json",
            HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),**self.headers)

    def setup_donor(self):
        donor=self.post("donors",{"branch_id":str(self.branch.id),
            "description":"Донор BMW 3","acquisition_cost_minor":100000}).json()["id"]
        bin_id=self.post("donor-bins",{"warehouse_id":str(self.warehouse.id),
            "code":"A-01"}).json()["id"]
        return donor,bin_id

    def test_cost_allocation_cannot_exceed_donor_cost(self):
        donor,bin_id=self.setup_donor()
        body={"donor_id":donor,"bin_id":bin_id,"inventory_code":"DONOR-001",
            "name":"Фара","allocated_cost_minor":90000,"target_price_minor":150000}
        self.assertEqual(self.post("salvaged-parts",body).status_code,201)
        body["inventory_code"]="DONOR-002"
        body["allocated_cost_minor"]=20000
        self.assertEqual(self.post("salvaged-parts",body).status_code,409)
        self.assertEqual(SalvagedPart.objects.count(),1)

    def test_unique_code_and_invalid_reserve(self):
        donor,bin_id=self.setup_donor()
        data={"donor_id":donor,"bin_id":bin_id,"inventory_code":"D-1",
              "name":"Крыло","allocated_cost_minor":10000,"target_price_minor":20000}
        part=self.post("salvaged-parts",data)
        self.assertEqual(part.status_code,201)
        self.assertEqual(self.post("salvaged-parts",data).status_code,409)
        pk=part.json()["id"]
        self.assertEqual(self.post(f"salvaged-parts/{pk}/reserve",{}).status_code,409)
        self.assertEqual(self.post(f"salvaged-parts/{pk}/approve",{}).status_code,200)
        self.assertEqual(self.post(f"salvaged-parts/{pk}/approve",{}).status_code,409)
