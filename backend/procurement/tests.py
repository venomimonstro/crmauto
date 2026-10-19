import uuid
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from identity.models import User,Organization,Branch,Membership
from inventory.models import Warehouse,Part,Stock,Movement
from procurement.models import GoodsReceipt,PurchaseOrder

@override_settings(BILLING_ENFORCE_WRITES=False)
class ProcurementContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="СТО А")
        self.other=Organization.objects.create(name="СТО Б")
        self.branch=Branch.objects.create(organization=self.org,name="Основной",code="main")
        self.warehouse=Warehouse.objects.create(organization=self.org,branch=self.branch,name="Основной")
        self.part=Part.objects.create(organization=self.org,sku="BRK-1",name="Колодки")
        self.user=User.objects.create_user("buyer@test.invalid","LongSafePassword23993!")
        Membership.objects.create(organization=self.org,user=self.user,role="owner")
        self.client=APIClient();self.client.force_authenticate(self.user)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}
        self.supplier=self.post("/api/v1/suppliers",{"name":"Поставщик"}).json()["id"]

    def post(self,path,data,key=None):
        return self.client.post(path,data,format="json",
           HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),**self.headers)

    def purchase(self):
        created=self.post("/api/v1/purchases",{
            "branch_id":str(self.branch.id),"warehouse_id":str(self.warehouse.id),
            "supplier_id":self.supplier,
        })
        self.assertEqual(created.status_code,201,created.content)
        return created.json()["id"]

    def prepare(self,qty=3):
        po=self.purchase()
        result=self.post(f"/api/v1/purchases/{po}/lines",{
            "part_id":str(self.part.id),"ordered":qty,"unit_cost_minor":120000
        })
        self.assertEqual(result.status_code,201,result.content)
        line=result.json()["lines"][0]["id"]
        self.assertEqual(self.post(f"/api/v1/purchases/{po}/actions/submit",{}).status_code,200)
        return po,line

    def test_partial_then_complete_receipt(self):
        po,line=self.prepare()
        first=self.post(f"/api/v1/purchases/{po}/receive",{"line_id":line,"quantity":1})
        self.assertEqual(first.status_code,201,first.content)
        self.assertEqual(first.json()["purchase"]["status"],"partial")
        second=self.post(f"/api/v1/purchases/{po}/receive",{"line_id":line,"quantity":2})
        self.assertEqual(second.status_code,201,second.content)
        self.assertEqual(second.json()["purchase"]["status"],"received")
        self.assertEqual(Stock.objects.get(warehouse=self.warehouse,part=self.part).quantity,3)
        self.assertEqual(GoodsReceipt.objects.filter(purchase_id=po).count(),2)

    def test_cannot_overreceive_or_repeat_with_new_key(self):
        po,line=self.prepare(2)
        response=self.post(f"/api/v1/purchases/{po}/receive",{"line_id":line,"quantity":3})
        self.assertEqual(response.status_code,409)
        self.assertEqual(Movement.objects.count(),0)
        key=str(uuid.uuid4())
        first=self.post(f"/api/v1/purchases/{po}/receive",{"line_id":line,"quantity":2},key)
        retry=self.post(f"/api/v1/purchases/{po}/receive",{"line_id":line,"quantity":2},key)
        self.assertEqual(first.status_code,201)
        self.assertEqual(retry.status_code,201)
        self.assertEqual(GoodsReceipt.objects.count(),1)

    def test_foreign_part_rejected(self):
        po=self.purchase()
        foreign=Part.objects.create(organization=self.other,sku="OTHER",name="Чужая деталь")
        result=self.post(f"/api/v1/purchases/{po}/lines",{
            "part_id":str(foreign.id),"ordered":1,"unit_cost_minor":100,
        })
        self.assertEqual(result.status_code,404)
