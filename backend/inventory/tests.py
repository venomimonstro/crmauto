import uuid
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import User,Organization,Branch,Membership
from crm.models import Customer,Vehicle
from scheduling.models import Appointment,Visit
from workorders.models import WorkOrder
from .models import Stock,Movement

@override_settings(BILLING_ENFORCE_WRITES=False)
class StockContracts(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name="СТО")
        self.branch=Branch.objects.create(organization=self.org,name="Основной",code="main")
        self.user=User.objects.create_user("stock@example.invalid","StrongPassword999999!")
        Membership.objects.create(organization=self.org,user=self.user,role="owner")
        self.client=APIClient();self.client.force_authenticate(self.user)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}
    def post(self,path,data,key=None):
        return self.client.post(path,data,format="json",HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),**self.headers)
    def setup_stock(self):
        wh=self.post("/api/v1/warehouses",{"branch_id":str(self.branch.id),"name":"Основной склад"}).json()["id"]
        part=self.post("/api/v1/parts",{"sku":"FILTER1","name":"Фильтр"}).json()["id"]
        item=self.post("/api/v1/stocks/receive",{"warehouse_id":wh,"part_id":part,"quantity":2})
        self.assertEqual(item.status_code,201,item.content)
        return item.json()["stock"]["id"]
    def setup_order(self):
        customer=Customer.objects.create(organization=self.org,name="Иван")
        car=Vehicle.objects.create(organization=self.org,make="VW",model="Golf")
        now=timezone.now()
        appointment=Appointment.objects.create(organization=self.org,branch=self.branch,customer=customer,
            vehicle=car,start_at=now,end_at=now+timedelta(hours=1),status="arrived")
        visit=Visit.objects.create(organization=self.org,branch=self.branch,customer=customer,vehicle=car,appointment=appointment)
        return WorkOrder.objects.create(organization=self.org,branch=self.branch,customer=customer,vehicle=car,
            visit=visit,created_by=self.user,status="in_progress")
    def test_receive_idempotent(self):
        stock_id=self.setup_stock()
        row=Stock.objects.get(pk=stock_id)
        self.assertEqual(row.quantity,2)
    def test_reserve_cannot_exceed_available(self):
        stock_id=self.setup_stock();order=self.setup_order()
        first=self.post("/api/v1/reservations",{"stock_id":stock_id,"order_id":str(order.id),"quantity":2})
        self.assertEqual(first.status_code,201,first.content)
        second=self.post("/api/v1/reservations",{"stock_id":stock_id,"order_id":str(order.id),"quantity":1})
        self.assertEqual(second.status_code,409)
        row=Stock.objects.get(pk=stock_id)
        self.assertEqual((row.quantity,row.reserved),(2,2))
    def test_issue_cannot_repeat(self):
        stock_id=self.setup_stock();order=self.setup_order()
        reserved=self.post("/api/v1/reservations",{"stock_id":stock_id,"order_id":str(order.id),"quantity":1}).json()
        self.assertEqual(self.post(f'/api/v1/reservations/{reserved["id"]}/issue',{}).status_code,200)
        self.assertEqual(self.post(f'/api/v1/reservations/{reserved["id"]}/issue',{}).status_code,409)
        row=Stock.objects.get(pk=stock_id)
        self.assertEqual((row.quantity,row.reserved),(1,0))
        self.assertEqual(Movement.objects.filter(kind="issue").count(),1)

    def test_draft_order_cannot_reserve_parts_before_approval(self):
        stock_id=self.setup_stock()
        order=self.setup_order()
        order.status="draft"
        order.save(update_fields=["status"])
        result=self.post("/api/v1/reservations",{
            "stock_id":stock_id,"order_id":str(order.id),"quantity":1})
        self.assertEqual(result.status_code,409,result.content)
        self.assertEqual(Stock.objects.get(pk=stock_id).reserved,0)

    def test_ready_order_cannot_issue_parts_after_quality_check(self):
        stock_id=self.setup_stock()
        order=self.setup_order()
        reservation=self.post("/api/v1/reservations",{
            "stock_id":stock_id,"order_id":str(order.id),"quantity":1})
        self.assertEqual(reservation.status_code,201,reservation.content)
        order.status="ready"
        order.save(update_fields=["status"])
        action=self.post(f'/api/v1/reservations/{reservation.json()["id"]}/issue',{})
        self.assertEqual(action.status_code,409,action.content)
        row=Stock.objects.get(pk=stock_id)
        self.assertEqual((row.quantity,row.reserved),(2,1))
        release=self.post(f'/api/v1/reservations/{reservation.json()["id"]}/release',{})
        self.assertEqual(release.status_code,200,release.content)
