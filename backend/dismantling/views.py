import re
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from core.commands import execute_command,BusinessConflict
from identity.models import Membership,AuditEvent
from identity.scope import TenantAPIView,require_roles
from scheduling.views import valid_branch
from inventory.models import Warehouse
from workorders.models import WorkOrder
from .models import Donor,StorageBin,SalvagedPart

EDIT=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.STOCK)
READ=EDIT+(Membership.Roles.ADVISER,Membership.Roles.VIEWER)

class DonorInput(serializers.Serializer):
    branch_id=serializers.UUIDField()
    vin=serializers.CharField(required=False,allow_blank=True,max_length=17)
    description=serializers.CharField(max_length=250)
    acquisition_cost_minor=serializers.IntegerField(min_value=0,max_value=10**14)

class BinInput(serializers.Serializer):
    warehouse_id=serializers.UUIDField()
    code=serializers.CharField(max_length=64)

class SalvageInput(serializers.Serializer):
    donor_id=serializers.UUIDField()
    bin_id=serializers.UUIDField()
    inventory_code=serializers.CharField(max_length=80)
    name=serializers.CharField(max_length=200)
    condition_notes=serializers.CharField(max_length=500,required=False,allow_blank=True)
    allocated_cost_minor=serializers.IntegerField(min_value=0,max_value=10**14)
    target_price_minor=serializers.IntegerField(min_value=0,max_value=10**14)

def audit(scope,user,event,obj):
    AuditEvent.objects.create(organization=scope.organization,actor=user,
                              event_type='dismantling.'+event,subject_id=obj.id)

def part_data(obj):
    return {'id':str(obj.id),'donor_id':str(obj.donor_id),'inventory_code':obj.inventory_code,
            'name':obj.name,'state':obj.state,'bin_id':str(obj.bin_id),
            'allocated_cost_minor':obj.allocated_cost_minor,'target_price_minor':obj.target_price_minor,
            'reserved_order_id':str(obj.reserved_order_id) if obj.reserved_order_id else None}

class Donors(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        branch=valid_branch(self.scope,request.query_params.get('branch_id'))
        records=Donor.objects.filter(organization=self.scope.organization,branch=branch).order_by('-created_at')[:100]
        return Response([{'id':str(x.id),'description':x.description,'vin':x.vin,
            'acquisition_cost_minor':x.acquisition_cost_minor,
            'allocated_cost_minor':x.parts.aggregate(amount=Sum('allocated_cost_minor'))['amount'] or 0} for x in records])
    def post(self,request):
        require_roles(self.scope,*EDIT)
        def op():
            s=DonorInput(data=request.data);s.is_valid(raise_exception=True);d=s.validated_data
            branch=valid_branch(self.scope,d['branch_id'])
            vin=d.get('vin','').strip().upper()
            if vin and not re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}',vin):
                raise ValidationError({'vin':'Некорректный VIN.'})
            obj=Donor.objects.create(organization=self.scope.organization,branch=branch,
                vin=vin,description=d['description'],acquisition_cost_minor=d['acquisition_cost_minor'])
            audit(self.scope,request.user,'donor_created',obj)
            return {'id':str(obj.id),'description':obj.description},201
        body,code=execute_command(request,self.scope,'donor.create',op)
        return Response(body,status=code)

class Bins(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        wh=get_object_or_404(Warehouse,pk=request.query_params.get('warehouse_id'),
                             organization=self.scope.organization)
        valid_branch(self.scope,wh.branch_id)
        return Response([{'id':str(x.id),'code':x.code} for x in
            StorageBin.objects.filter(organization=self.scope.organization,warehouse=wh).order_by('code')])
    def post(self,request):
        require_roles(self.scope,*EDIT)
        def op():
            s=BinInput(data=request.data);s.is_valid(raise_exception=True);d=s.validated_data
            wh=get_object_or_404(Warehouse,pk=d['warehouse_id'],organization=self.scope.organization)
            valid_branch(self.scope,wh.branch_id)
            if StorageBin.objects.filter(warehouse=wh,code=d['code']).exists():
                raise BusinessConflict('Такая ячейка уже существует.')
            obj=StorageBin.objects.create(organization=self.scope.organization,warehouse=wh,code=d['code'])
            audit(self.scope,request.user,'bin_created',obj)
            return {'id':str(obj.id),'code':obj.code},201
        body,code=execute_command(request,self.scope,'donor.bin',op)
        return Response(body,status=code)

class SalvageParts(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        donor=get_object_or_404(Donor,pk=request.query_params.get('donor_id'),organization=self.scope.organization)
        valid_branch(self.scope,donor.branch_id)
        return Response([part_data(x) for x in donor.parts.order_by('name')[:200]])
    def post(self,request):
        require_roles(self.scope,*EDIT)
        def op():
            s=SalvageInput(data=request.data);s.is_valid(raise_exception=True);d=s.validated_data
            donor=get_object_or_404(Donor,pk=d['donor_id'],organization=self.scope.organization)
            valid_branch(self.scope,donor.branch_id)
            bin=get_object_or_404(StorageBin.objects.select_related('warehouse'),pk=d['bin_id'],
                                  organization=self.scope.organization)
            if bin.warehouse.branch_id!=donor.branch_id:
                raise BusinessConflict('Деталь нельзя поместить в филиал другого донора.')
            if SalvagedPart.objects.filter(organization=self.scope.organization,
                inventory_code=d['inventory_code']).exists():
                raise BusinessConflict('Учётный номер уже существует.')
            allocated=donor.parts.aggregate(total=Sum('allocated_cost_minor'))['total'] or 0
            if allocated+d['allocated_cost_minor']>donor.acquisition_cost_minor+donor.extra_cost_minor:
                raise BusinessConflict('Распределённая себестоимость превышает затраты донора.')
            obj=SalvagedPart.objects.create(organization=self.scope.organization,donor=donor,bin=bin,
                inventory_code=d['inventory_code'],name=d['name'],
                condition_notes=d.get('condition_notes',''),
                allocated_cost_minor=d['allocated_cost_minor'],target_price_minor=d['target_price_minor'])
            audit(self.scope,request.user,'part_recorded',obj)
            return part_data(obj),201
        body,code=execute_command(request,self.scope,'donor.part_record',op)
        return Response(body,status=code)

class PartAction(TenantAPIView):
    def post(self,request,pk,action):
        require_roles(self.scope,*EDIT)
        if action not in ('approve','reserve','release','retire'):
            raise ValidationError({'action':'Неизвестный переход.'})
        def op():
            obj=get_object_or_404(SalvagedPart.objects.select_related('donor','bin__warehouse'),
                pk=pk,organization=self.scope.organization)
            valid_branch(self.scope,obj.donor.branch_id)
            moves={
                'approve':('recorded','available'),
                'reserve':('available','reserved'),
                'release':('reserved','available'),
                'retire':('available','retired'),
            }
            before,after=moves[action]
            if obj.state!=before:
                raise BusinessConflict('Деталь уже занята или состояние не допускает действие.')
            if action=='reserve':
                order=get_object_or_404(WorkOrder,pk=request.data.get('order_id'),
                    organization=self.scope.organization,branch=obj.donor.branch)
                if order.status in ('cancelled','delivered'):
                    raise BusinessConflict('Нельзя резервировать на закрытый заказ.')
                obj.reserved_order=order
            if action=='release':obj.reserved_order=None
            obj.state=after
            obj.save(update_fields=['state','reserved_order'])
            audit(self.scope,request.user,'part_'+action,obj)
            return part_data(obj),200
        body,code=execute_command(request,self.scope,'donor.part.'+str(pk)+'.'+action,op)
        return Response(body,status=code)
