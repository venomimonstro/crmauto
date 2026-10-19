"""Scenario-driven API integration contracts. Requires an actual Django test DB."""
from datetime import timedelta
from uuid import uuid4
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from identity.models import Branch, Membership, Organization, User
from billing.models import Plan, Subscription
from crm.models import Customer, Vehicle
from finance.models import Invoice, Movement


@override_settings(BILLING_ENFORCE_WRITES=True)
class WorkshopOwnerJourney(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user("owner-journey@test.invalid","Safe-Long-Password-9901!")
        self.org=Organization.objects.create(name="Тестовый автосервис")
        self.branch=Branch.objects.create(organization=self.org,name="СТО №1",code="main")
        Membership.objects.create(user=self.owner,organization=self.org,role="owner")
        plan=Plan.objects.create(code="scenario",name="Тестовый тариф",price_minor=99000)
        Subscription.objects.create(organization=self.org,plan=plan,state="active",
            paid_through=timezone.now()+timedelta(days=7))
        self.client=APIClient()
        self.client.force_authenticate(self.owner)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.org.id)}

    def post(self,path,data):
        return self.client.post("/api/v1/"+path,data,format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid4()),**self.headers)

    def assert_created(self, response):
        self.assertEqual(response.status_code,201,response.content)
        return response.json()

    def test_owner_from_appointment_to_partial_cash_payment(self):
        customer=self.assert_created(self.post("customers",{
            "name":"Иван Петров","kind":"person","phone":"+79991112233"}))
        vehicle=self.assert_created(self.post("vehicles",{
            "make":"Toyota","model":"Camry","owner_id":customer["id"]}))
        bay=self.assert_created(self.post("bays",{
            "branch_id":str(self.branch.id),"name":"Подъёмник 1"}))
        start=timezone.now()+timedelta(days=1)
        payload={"branch_id":str(self.branch.id),"customer_id":customer["id"],
            "vehicle_id":vehicle["id"],"bay_id":bay["id"],
            "start_at":start.isoformat(),"end_at":(start+timedelta(hours=2)).isoformat()}
        booked=self.assert_created(self.post("appointments",payload))
        conflicting=self.post("appointments",payload)
        self.assertEqual(conflicting.status_code,409,conflicting.content)
        arrived=self.post("appointments/"+booked["id"]+"/arrive",{})
        self.assertEqual(arrived.status_code,200,arrived.content)
        visit_id=arrived.json()["visit_id"]
        order=self.assert_created(self.post("workorders",{
            "visit_id":visit_id,"complaint":"Стук передней подвески"}))
        estimate=self.assert_created(self.post("workorders/"+order["id"]+"/lines",{
            "kind":"labor","title":"Диагностика","quantity":"1.500",
            "unit_price_minor":120000}))
        self.assertEqual(estimate["total_minor"],180000)
        self.assertEqual(self.post("workorders/"+order["id"]+"/actions/start",{}).status_code,409)
        self.assertEqual(self.post("workorders/"+order["id"]+"/actions/submit",{}).status_code,200)
        self.assertEqual(self.post("workorders/"+order["id"]+"/actions/approve",{
            "reference":"Проверенный акт согласования №1"}).status_code,200)
        self.assertEqual(self.post("workorders/"+order["id"]+"/actions/start",{}).status_code,200)
        invoice=self.assert_created(self.post("invoices",{"order_id":order["id"]}))
        self.assertEqual(invoice["amount_minor"],180000)
        box=self.assert_created(self.post("cashboxes",{"branch_id":str(self.branch.id),"name":"Наличные"}))
        first=self.assert_created(self.post("payments",{"invoice_id":invoice["id"],
            "cashbox_id":box["id"],"method":"cash","amount_minor":60000,
            "reference":"Наличные получены в кассу, тест"}))
        self.assertEqual(first["invoice"]["debt_minor"],120000)
        self.assertEqual(self.post("payments",{"invoice_id":invoice["id"],
            "cashbox_id":box["id"],"method":"cash","amount_minor":130000,
            "reference":"Переплата"}).status_code,409)
        self.assertEqual(Movement.objects.filter(kind="income").count(),1)
        self.assertEqual(Invoice.objects.get(pk=invoice["id"]).paid_minor,60000)

    def test_unverified_card_payment_rejected(self):
        customer=Customer.objects.create(organization=self.org,name="Сергей")
        car=Vehicle.objects.create(organization=self.org,make="Audi",model="A4")
        from scheduling.models import Appointment, Visit
        from workorders.models import WorkOrder, Estimate
        now=timezone.now()
        appointment=Appointment.objects.create(organization=self.org,branch=self.branch,
            customer=customer,vehicle=car,start_at=now,end_at=now+timedelta(hours=1))
        visit=Visit.objects.create(organization=self.org,branch=self.branch,
            customer=customer,vehicle=car,appointment=appointment)
        order=WorkOrder.objects.create(organization=self.org,branch=self.branch,visit=visit,
            customer=customer,vehicle=car,created_by=self.owner,status="approved")
        Estimate.objects.create(order=order,revision=1,state="approved",total_minor=10000)
        invoice=self.assert_created(self.post("invoices",{"order_id":str(order.id)}))
        box=self.assert_created(self.post("cashboxes",{"branch_id":str(self.branch.id),"name":"Касса"}))
        attempt=self.post("payments",{"invoice_id":invoice["id"],"cashbox_id":box["id"],
            "method":"card","amount_minor":10000,"reference":"Без PSP"})
        self.assertEqual(attempt.status_code,400,attempt.content)
        self.assertFalse(Movement.objects.exists())

    def test_full_payment_partial_refund_and_repayment(self):
        """Positive: a later repayment is legal, while net paid never exceeds invoice."""
        from scheduling.models import Appointment, Visit
        from workorders.models import WorkOrder, Estimate
        customer=Customer.objects.create(organization=self.org,name="Повторная оплата")
        car=Vehicle.objects.create(organization=self.org,make="Kia",model="Rio")
        now=timezone.now()
        appointment=Appointment.objects.create(organization=self.org,branch=self.branch,
            customer=customer,vehicle=car,start_at=now,end_at=now+timedelta(hours=1))
        visit=Visit.objects.create(organization=self.org,branch=self.branch,appointment=appointment,
            customer=customer,vehicle=car)
        order=WorkOrder.objects.create(organization=self.org,branch=self.branch,
            visit=visit,customer=customer,vehicle=car,created_by=self.owner,status="approved")
        Estimate.objects.create(order=order,revision=1,state="approved",total_minor=10000)
        invoice=self.assert_created(self.post("invoices",{"order_id":str(order.id)}))
        box=self.assert_created(self.post("cashboxes",{
            "branch_id":str(self.branch.id),"name":"Наличные"}))
        full=self.assert_created(self.post("payments",{
            "invoice_id":invoice["id"],"cashbox_id":box["id"],"amount_minor":10000,
            "method":"cash","reference":"Первая оплата"}))
        refunded=self.assert_created(self.post("refunds",{
            "source_id":full["movement_id"],"amount_minor":4000,
            "reference":"Частичный возврат"}))
        self.assertEqual(refunded["invoice"]["debt_minor"],4000)
        repeat=self.assert_created(self.post("payments",{
            "invoice_id":invoice["id"],"cashbox_id":box["id"],"amount_minor":4000,
            "method":"cash","reference":"Повторная оплата"}))
        self.assertEqual(repeat["invoice"]["debt_minor"],0)
        row=Invoice.objects.get(pk=invoice["id"])
        self.assertEqual(row.paid_minor,14000)
        self.assertEqual(row.refunded_minor,4000)
        self.assertEqual(Movement.objects.filter(invoice=row).count(),3)
        over=self.post("payments",{
            "invoice_id":invoice["id"],"cashbox_id":box["id"],"amount_minor":1,
            "method":"cash","reference":"Попытка переплаты"})
        self.assertEqual(over.status_code,409,over.content)
