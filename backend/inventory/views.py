from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from core.commands import execute_command,BusinessConflict
from identity.models import Membership,AuditEvent
from identity.scope import TenantAPIView,require_roles
from scheduling.views import valid_branch
from workorders.models import WorkOrder
from .models import Warehouse,Part,Stock,Reservation,Movement
from .serializers import WarehouseSerializer,PartSerializer,StockSerializer,ReservationSerializer

EDIT=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.STOCK)
READ=EDIT+(Membership.Roles.ADVISER,Membership.Roles.VIEWER)

def audit(scope,user,kind,obj):
    AuditEvent.objects.create(organization=scope.organization,actor=user,event_type="inventory."+kind,subject_id=obj.id)

def allowed_stock(scope,pk):
    row=get_object_or_404(Stock.objects.select_related("warehouse","part"),pk=pk,organization_id=scope.organization_id)
    valid_branch(scope,row.warehouse.branch_id)
    return row

class Warehouses(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        branch=valid_branch(self.scope,request.query_params.get("branch_id"))
        return Response(WarehouseSerializer(Warehouse.objects.filter(organization=self.scope.organization,branch=branch),many=True).data)
    def post(self,request):
        require_roles(self.scope,*EDIT)
        def op():
            branch=valid_branch(self.scope,request.data.get("branch_id"))
            ser=WarehouseSerializer(data=request.data);ser.is_valid(raise_exception=True)
            warehouse=Warehouse.objects.create(organization=self.scope.organization,branch=branch,name=ser.validated_data["name"])
            audit(self.scope,request.user,"warehouse_created",warehouse)
            return WarehouseSerializer(warehouse).data,201
        result,code=execute_command(request,self.scope,"warehouse.create",op)
        return Response(result,status=code)

class Parts(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        items=Part.objects.filter(organization=self.scope.organization).order_by("name")[:200]
        return Response(PartSerializer(items,many=True).data)
    def post(self,request):
        require_roles(self.scope,*EDIT)
        def op():
            ser=PartSerializer(data=request.data);ser.is_valid(raise_exception=True)
            try:
                part=Part.objects.create(organization=self.scope.organization,**ser.validated_data)
            except IntegrityError as exc:
                raise BusinessConflict("Артикул уже существует.") from exc
            audit(self.scope,request.user,"part_created",part)
            return PartSerializer(part).data,201
        result,code=execute_command(request,self.scope,"part.create",op)
        return Response(result,status=code)

class Stocks(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        warehouse=get_object_or_404(Warehouse,pk=request.query_params.get("warehouse_id"),organization=self.scope.organization)
        valid_branch(self.scope,warehouse.branch_id)
        items=Stock.objects.filter(organization=self.scope.organization,warehouse=warehouse).order_by("part__name")[:200]
        return Response(StockSerializer(items,many=True).data)

class Receive(TenantAPIView):
    def post(self,request):
        require_roles(self.scope,*EDIT)
        def op():
            warehouse=get_object_or_404(Warehouse,pk=request.data.get("warehouse_id"),organization=self.scope.organization,active=True)
            valid_branch(self.scope,warehouse.branch_id)
            part=get_object_or_404(Part,pk=request.data.get("part_id"),organization=self.scope.organization)
            try:
                qty=int(request.data.get("quantity",0))
            except (ValueError,TypeError):
                raise ValidationError({"quantity":"Требуется целое число."})
            if qty<=0 or qty>1000000:
                raise ValidationError({"quantity":"Количество должно быть от 1 до 1000000."})
            row,_=Stock.objects.select_for_update().get_or_create(organization=self.scope.organization,warehouse=warehouse,part=part,defaults={"quantity":0})
            row.quantity+=qty;row.save(update_fields=["quantity"])
            movement=Movement.objects.create(organization=self.scope.organization,stock=row,kind="receipt",quantity=qty)
            audit(self.scope,request.user,"received",movement)
            return {"stock":StockSerializer(row).data,"movement_id":str(movement.id)},201
        body,code=execute_command(request,self.scope,"inventory.receive",op)
        return Response(body,status=code)

class Reserve(TenantAPIView):
    def post(self,request):
        require_roles(self.scope,*EDIT+(Membership.Roles.ADVISER,))
        def op():
            row=allowed_stock(self.scope,request.data.get("stock_id"))
            row=Stock.objects.select_for_update().get(pk=row.pk)
            order=get_object_or_404(WorkOrder,pk=request.data.get("order_id"),organization=self.scope.organization)
            valid_branch(self.scope,order.branch_id)
            if order.branch_id!=row.warehouse.branch_id or order.status not in ("approved","in_progress"):
                raise BusinessConflict("Нельзя резервировать для этого заказ-наряда.")
            try: qty=int(request.data.get("quantity",0))
            except (ValueError,TypeError):raise ValidationError({"quantity":"Необходимо целое число."})
            if qty<=0 or qty>row.quantity-row.reserved:
                raise BusinessConflict("Недостаточно доступных остатков.")
            r=Reservation.objects.create(organization=self.scope.organization,stock=row,order=order,quantity=qty)
            row.reserved+=qty;row.save(update_fields=["reserved"])
            audit(self.scope,request.user,"reserved",r)
            return ReservationSerializer(r).data,201
        body,code=execute_command(request,self.scope,"inventory.reserve",op)
        return Response(body,status=code)

class ReservationAction(TenantAPIView):
    def post(self,request,pk,action):
        require_roles(self.scope,*EDIT+(Membership.Roles.ADVISER,))
        if action not in ("release","issue"):
            raise ValidationError({"action":"Неизвестное действие."})
        def op():
            r=get_object_or_404(Reservation.objects.select_related("stock__warehouse"),pk=pk,organization=self.scope.organization)
            valid_branch(self.scope,r.stock.warehouse.branch_id)
            if r.state!="active":raise BusinessConflict("Резерв уже обработан.")
            row=Stock.objects.select_for_update().get(pk=r.stock_id)
            if row.reserved<r.quantity or (action=="issue" and row.quantity<r.quantity):
                raise BusinessConflict("Остатки требуют сверки.")
            row.reserved-=r.quantity
            movement=None
            if action=="issue":
                if r.order.status not in ("in_progress","qa"):
                    raise BusinessConflict("Расход только в процессе ремонта.")
                row.quantity-=r.quantity
                movement=Movement.objects.create(organization=self.scope.organization,stock=row,reservation=r,kind="issue",quantity=r.quantity)
            row.save(update_fields=["reserved","quantity"])
            r.state="issued" if action=="issue" else "released";r.save(update_fields=["state"])
            audit(self.scope,request.user,action,r)
            return {"reservation":ReservationSerializer(r).data,"movement_id":str(movement.id) if movement else None},200
        body,code=execute_command(request,self.scope,f"inventory.reservation.{pk}.{action}",op)
        return Response(body,status=code)
