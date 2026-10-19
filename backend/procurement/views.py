from django.shortcuts import get_object_or_404
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from core.commands import BusinessConflict,execute_command
from identity.scope import TenantAPIView,require_roles
from identity.models import Membership,AuditEvent
from scheduling.views import valid_branch
from inventory.models import Warehouse,Part,Stock,Movement
from .models import Supplier,PurchaseOrder,PurchaseLine,GoodsReceipt

MANAGE=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.STOCK)
READ=MANAGE+(Membership.Roles.ADVISER,Membership.Roles.VIEWER)

class SupplierInput(serializers.Serializer):
    name=serializers.CharField(max_length=200)
    inn=serializers.RegexField(r"^(?:\d{10}|\d{12})$",required=False,allow_blank=True)
    phone=serializers.CharField(max_length=32,required=False,allow_blank=True)

class PurchaseInput(serializers.Serializer):
    branch_id=serializers.UUIDField()
    warehouse_id=serializers.UUIDField()
    supplier_id=serializers.UUIDField()
    supplier_reference=serializers.CharField(max_length=100,required=False,allow_blank=True)

class LineInput(serializers.Serializer):
    part_id=serializers.UUIDField()
    ordered=serializers.IntegerField(min_value=1,max_value=1000000)
    unit_cost_minor=serializers.IntegerField(min_value=0,max_value=10**12)

class ReceiptInput(serializers.Serializer):
    line_id=serializers.UUIDField()
    quantity=serializers.IntegerField(min_value=1,max_value=1000000)

def audit(scope,user,kind,subject,extra=None):
    AuditEvent.objects.create(organization=scope.organization,actor=user,
        event_type="procurement."+kind,subject_id=subject.id,details=extra or {})

def purchase_data(order):
    return {"id":str(order.id),"supplier_id":str(order.supplier_id),
        "branch_id":str(order.branch_id),"warehouse_id":str(order.warehouse_id),
        "status":order.status,"version":order.version,
        "lines":[{"id":str(x.id),"part_id":str(x.part_id),"ordered":x.ordered,
                  "received":x.received,"unit_cost_minor":x.unit_cost_minor}
                  for x in order.lines.order_by("id")]}

def get_purchase(scope,pk):
    item=get_object_or_404(PurchaseOrder.objects.select_related("warehouse"),
                           pk=pk,organization_id=scope.organization_id)
    valid_branch(scope,item.branch_id)
    return item

class Suppliers(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        rows=Supplier.objects.filter(organization=self.scope.organization).order_by("name")[:200]
        return Response([{"id":str(x.id),"name":x.name,"inn":x.inn,"phone":x.phone} for x in rows])
    def post(self,request):
        require_roles(self.scope,*MANAGE)
        def op():
            ser=SupplierInput(data=request.data);ser.is_valid(raise_exception=True)
            obj=Supplier.objects.create(organization=self.scope.organization,**ser.validated_data)
            audit(self.scope,request.user,"supplier_created",obj)
            return {"id":str(obj.id),"name":obj.name},201
        body,code=execute_command(request,self.scope,"supplier.create",op)
        return Response(body,status=code)

class Purchases(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        branch=valid_branch(self.scope,request.query_params.get("branch_id"))
        rows=PurchaseOrder.objects.filter(organization=self.scope.organization,branch=branch).order_by("-created_at")[:100]
        return Response([purchase_data(x) for x in rows])
    def post(self,request):
        require_roles(self.scope,*MANAGE)
        def op():
            ser=PurchaseInput(data=request.data);ser.is_valid(raise_exception=True);data=ser.validated_data
            branch=valid_branch(self.scope,data["branch_id"])
            warehouse=get_object_or_404(Warehouse,pk=data["warehouse_id"],branch=branch,
                                       organization=self.scope.organization,active=True)
            supplier=get_object_or_404(Supplier,pk=data["supplier_id"],
                                       organization=self.scope.organization,active=True)
            obj=PurchaseOrder.objects.create(organization=self.scope.organization,branch=branch,
                warehouse=warehouse,supplier=supplier,
                supplier_reference=data.get("supplier_reference",""))
            audit(self.scope,request.user,"created",obj)
            return purchase_data(obj),201
        body,code=execute_command(request,self.scope,"purchase.create",op)
        return Response(body,status=code)

class PurchaseDetail(TenantAPIView):
    def get(self,request,pk):
        require_roles(self.scope,*READ)
        return Response(purchase_data(get_purchase(self.scope,pk)))

class AddLine(TenantAPIView):
    def post(self,request,pk):
        require_roles(self.scope,*MANAGE)
        def op():
            order=get_purchase(self.scope,pk)
            if order.status!="draft":raise BusinessConflict("Состав согласованного заказа неизменяем.")
            ser=LineInput(data=request.data);ser.is_valid(raise_exception=True);data=ser.validated_data
            part=get_object_or_404(Part,pk=data["part_id"],organization=self.scope.organization)
            if PurchaseLine.objects.filter(purchase=order,part=part).exists():
                raise BusinessConflict("Деталь уже включена в заказ.")
            line=PurchaseLine.objects.create(purchase=order,part=part,
                ordered=data["ordered"],unit_cost_minor=data["unit_cost_minor"])
            order.version+=1;order.save(update_fields=["version"])
            audit(self.scope,request.user,"line_added",order,{"line_id":str(line.id)})
            return purchase_data(order),201
        body,code=execute_command(request,self.scope,f"purchase.{pk}.line",op)
        return Response(body,status=code)

class PurchaseAction(TenantAPIView):
    def post(self,request,pk,action):
        require_roles(self.scope,*MANAGE)
        if action not in ("submit","cancel"):raise ValidationError({"action":"Неизвестная операция."})
        def op():
            order=get_purchase(self.scope,pk)
            if order.status!="draft":raise BusinessConflict("Заказ уже отправлен.")
            if action=="submit":
                if not order.lines.exists():raise BusinessConflict("Заказ поставщику пуст.")
                order.status="ordered"
            else:order.status="cancelled"
            order.version+=1;order.save(update_fields=["status","version"])
            audit(self.scope,request.user,action,order)
            return purchase_data(order),200
        body,code=execute_command(request,self.scope,f"purchase.{pk}.{action}",op)
        return Response(body,status=code)

class ReceivePurchase(TenantAPIView):
    def post(self,request,pk):
        require_roles(self.scope,*MANAGE)
        def op():
            order=get_purchase(self.scope,pk)
            if order.status not in ("ordered","partial"):
                raise BusinessConflict("Приёмка возможна только по открытому заказу.")
            ser=ReceiptInput(data=request.data);ser.is_valid(raise_exception=True);data=ser.validated_data
            line=get_object_or_404(PurchaseLine,pk=data["line_id"],purchase=order)
            qty=data["quantity"]
            if qty>line.ordered-line.received:
                raise BusinessConflict("Поступило больше заказанного. Требуется отдельное согласование.")
            stock,_=Stock.objects.select_for_update().get_or_create(
                organization=self.scope.organization,warehouse=order.warehouse,part=line.part,
                defaults={"quantity":0})
            stock.quantity+=qty;stock.save(update_fields=["quantity"])
            movement=Movement.objects.create(organization=self.scope.organization,stock=stock,
                                            kind="receipt",quantity=qty)
            receipt=GoodsReceipt.objects.create(organization=self.scope.organization,purchase=order,
                movement=movement,part=line.part,quantity=qty,unit_cost_minor=line.unit_cost_minor)
            line.received+=qty;line.save(update_fields=["received"])
            order.status=("received" if not PurchaseLine.objects.filter(purchase=order,received__lt=0).exists()
                and all(x.received==x.ordered for x in order.lines.all()) else "partial")
            order.version+=1;order.save(update_fields=["status","version"])
            audit(self.scope,request.user,"goods_received",receipt,
                  {"purchase_id":str(order.id),"movement_id":str(movement.id)})
            return {"purchase":purchase_data(order),"receipt_id":str(receipt.id),
                    "movement_id":str(movement.id)},201
        body,code=execute_command(request,self.scope,f"purchase.{pk}.receive",op)
        return Response(body,status=code)
