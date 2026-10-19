from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from core.commands import execute_command,BusinessConflict
from identity.models import Membership,AuditEvent,MemberBranch
from identity.scope import TenantAPIView,require_roles
from scheduling.views import valid_branch
from crm.models import Customer,Vehicle,Ownership
from .models import Shift,TireSet

ADMIN=(Membership.Roles.OWNER,Membership.Roles.MANAGER)
STAFF=ADMIN+(Membership.Roles.ADVISER,)
READ=STAFF+(Membership.Roles.VIEWER,Membership.Roles.MECHANIC)

class TireIn(serializers.Serializer):
    branch_id=serializers.UUIDField()
    customer_id=serializers.UUIDField()
    vehicle_id=serializers.UUIDField(required=False,allow_null=True)
    code=serializers.CharField(max_length=80)
    pieces=serializers.IntegerField(min_value=1,max_value=16)
    description=serializers.CharField(max_length=300)
    storage_location=serializers.CharField(max_length=120)

class ShiftIn(serializers.Serializer):
    branch_id=serializers.UUIDField()
    membership_id=serializers.UUIDField()
    begins=serializers.DateTimeField()
    ends=serializers.DateTimeField()
    def validate(self,attrs):
        if attrs['ends']<=attrs['begins']:
            raise serializers.ValidationError('Конец смены должен быть позже начала.')
        return attrs

def audit(scope,user,kind,entity):
    AuditEvent.objects.create(organization=scope.organization,actor=user,event_type='workforce.'+kind,subject_id=entity.id)

class Tires(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        branch=valid_branch(self.scope,request.query_params.get('branch_id'))
        qs=TireSet.objects.filter(organization=self.scope.organization,branch=branch).order_by('-received_at')[:200]
        return Response([{'id':str(x.id),'code':x.code,'customer_id':str(x.customer_id),
           'vehicle_id':str(x.vehicle_id) if x.vehicle_id else None,'pieces':x.pieces,
           'description':x.description,'storage_location':x.storage_location,'state':x.state} for x in qs])
    def post(self,request):
        require_roles(self.scope,*STAFF)
        def op():
            s=TireIn(data=request.data);s.is_valid(raise_exception=True);d=s.validated_data
            branch=valid_branch(self.scope,d['branch_id'])
            customer=get_object_or_404(Customer,pk=d['customer_id'],organization=self.scope.organization)
            vehicle=None
            if d.get('vehicle_id'):
                vehicle=get_object_or_404(Vehicle,pk=d['vehicle_id'],organization=self.scope.organization)
                if not Ownership.objects.filter(organization=self.scope.organization,
                    vehicle=vehicle,customer=customer,ended_on__isnull=True).exists():
                    raise BusinessConflict("Автомобиль не принадлежит выбранному клиенту. Проверьте карточку автомобиля.")
            if TireSet.objects.filter(organization=self.scope.organization,code=d['code']).exists():
                raise BusinessConflict('Код комплекта уже занят.')
            obj=TireSet.objects.create(organization=self.scope.organization,branch=branch,
                customer=customer,vehicle=vehicle,code=d['code'],pieces=d['pieces'],
                description=d['description'],storage_location=d['storage_location'])
            audit(self.scope,request.user,'tires_received',obj)
            return {'id':str(obj.id),'state':obj.state},201
        result,code=execute_command(request,self.scope,'tires.receive',op)
        return Response(result,status=code)

class TireRelease(TenantAPIView):
    def post(self,request,pk):
        require_roles(self.scope,*STAFF)
        def op():
            obj=get_object_or_404(TireSet,pk=pk,organization=self.scope.organization)
            valid_branch(self.scope,obj.branch_id)
            if obj.state!='stored':raise BusinessConflict('Комплект уже выдан.')
            obj.state='released';obj.released_at=timezone.now()
            obj.save(update_fields=['state','released_at'])
            audit(self.scope,request.user,'tires_released',obj)
            return {'id':str(obj.id),'state':obj.state},200
        result,code=execute_command(request,self.scope,'tires.release.'+str(pk),op)
        return Response(result,status=code)

class Shifts(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        branch=valid_branch(self.scope,request.query_params.get('branch_id'))
        qs=Shift.objects.filter(organization=self.scope.organization,branch=branch).order_by('begins')[:200]
        return Response([{'id':str(x.id),'membership_id':str(x.membership_id),
            'begins':x.begins.isoformat(),'ends':x.ends.isoformat(),'state':x.state} for x in qs])
    def post(self,request):
        require_roles(self.scope,*ADMIN)
        def op():
            s=ShiftIn(data=request.data);s.is_valid(raise_exception=True);d=s.validated_data
            branch=valid_branch(self.scope,d['branch_id'])
            member=get_object_or_404(Membership,pk=d['membership_id'],organization=self.scope.organization,is_active=True)
            if member.role not in ('owner','manager') and not MemberBranch.objects.filter(membership=member,branch=branch).exists():
                raise BusinessConflict('Сотрудник не привязан к филиалу.')
            if Shift.objects.filter(membership=member,branch=branch,state='planned',
                   begins__lt=d['ends'],ends__gt=d['begins']).exists():
                raise BusinessConflict('Смена пересекается с другой сменой сотрудника.')
            obj=Shift.objects.create(organization=self.scope.organization,branch=branch,membership=member,
                                     begins=d['begins'],ends=d['ends'])
            audit(self.scope,request.user,'shift_planned',obj)
            return {'id':str(obj.id),'state':obj.state},201
        result,code=execute_command(request,self.scope,'shift.create',op)
        return Response(result,status=code)
