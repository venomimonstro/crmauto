from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from core.commands import BusinessConflict,execute_command
from identity.models import Membership
from identity.scope import TenantAPIView,require_roles
from scheduling.models import Visit
from scheduling.views import valid_branch
from .models import WorkOrder,EstimateLine
from .serializers import OrderSerializer,OrderCreateSerializer,LineWriteSerializer,EstimateSerializer
from .services import create_revision,draft,recalculate,total_minor,event,transition

EDIT=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.ADVISER)
READ=EDIT+(Membership.Roles.MECHANIC,Membership.Roles.VIEWER)

def get_order(scope,pk):
    obj=get_object_or_404(WorkOrder.objects.select_related("branch","visit","customer","vehicle"),pk=pk,
                          organization_id=scope.organization_id)
    valid_branch(scope,obj.branch_id)
    return obj

class Orders(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        branch=valid_branch(self.scope,request.query_params.get("branch_id"))
        rows=WorkOrder.objects.filter(organization=self.scope.organization,branch=branch).order_by("-created_at")[:100]
        return Response(OrderSerializer(rows,many=True).data)
    def post(self,request):
        require_roles(self.scope,*EDIT)
        def create():
            serializer=OrderCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            d=serializer.validated_data
            visit=get_object_or_404(Visit,pk=d["visit_id"],organization_id=self.scope.organization_id)
            valid_branch(self.scope,visit.branch_id)
            if visit.status!="open":
                raise BusinessConflict("Визит уже закрыт.")
            if WorkOrder.objects.filter(visit=visit).exists():
                raise BusinessConflict("Для визита уже существует заказ-наряд.")
            order=WorkOrder.objects.create(organization=visit.organization,branch=visit.branch,
                visit=visit,customer=visit.customer,vehicle=visit.vehicle,created_by=request.user,
                complaint=d.get("complaint",""),odometer_km=d.get("odometer_km"),
                existing_damage=d.get("existing_damage",""))
            create_revision(order,request.user)
            event(order,request.user,"created")
            return OrderSerializer(order).data,status.HTTP_201_CREATED
        body,code=execute_command(request,self.scope,"workorder.create",create)
        return Response(body,status=code)

class OrderDetail(TenantAPIView):
    def get(self,request,pk):
        require_roles(self.scope,*READ)
        order=get_order(self.scope,pk)
        return Response({"order":OrderSerializer(order).data,
                         "estimates":EstimateSerializer(order.estimates.order_by("revision"),many=True).data,
                         "history":[{"from":t.previous,"to":t.current,"at":t.occurred_at} for t in order.transitions.order_by("occurred_at")]})

class LineAdd(TenantAPIView):
    def post(self,request,pk):
        require_roles(self.scope,*EDIT)
        def create():
            order=get_order(self.scope,pk)
            if order.status!="draft":
                raise BusinessConflict("Позиции изменяются только в черновике.")
            estimate=draft(order)
            if not estimate:
                raise BusinessConflict("Нет редактируемой сметы.")
            ser=LineWriteSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            d=ser.validated_data
            line=EstimateLine.objects.create(estimate=estimate,kind=d["kind"],title=d["title"],
                quantity=d["quantity"],unit_price_minor=d["unit_price_minor"],
                total_minor=total_minor(d["quantity"],d["unit_price_minor"]))
            recalculate(estimate)
            order.version+=1;order.save(update_fields=["version"])
            event(order,request.user,"line_added",{"line_id":str(line.pk)})
            return EstimateSerializer(estimate).data,status.HTTP_201_CREATED
        body,code=execute_command(request,self.scope,f"workorder.line.{pk}",create)
        return Response(body,status=code)

class Actions(TenantAPIView):
    def post(self,request,pk,action):
        require_roles(self.scope,*EDIT)
        if action not in ("submit","approve","reject","revise","start","qa","rework","ready","deliver","cancel"):
            raise ValidationError({"action":"Операция не поддерживается."})
        def perform():
            order=get_order(self.scope,pk)
            transition(order,request.user,action,
                       reference=str(request.data.get("reference","")),
                       reason=str(request.data.get("reason",""))[:500])
            return {"id":str(order.id),"status":order.status,"version":order.version},200
        body,code=execute_command(request,self.scope,f"workorder.{pk}.{action}",perform)
        return Response(body,status=code)
