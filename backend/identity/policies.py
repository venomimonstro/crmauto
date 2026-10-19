"""Versioned workshop service/warranty terms; never auto-sign or infer consent."""
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response
from core.commands import execute_command,BusinessConflict
from identity.models import Membership,ServicePolicy
from identity.scope import TenantAPIView,require_roles

READ=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.ADVISER,Membership.Roles.VIEWER)
EDIT=(Membership.Roles.OWNER,Membership.Roles.MANAGER)
class PolicyPayload(serializers.Serializer):
    service_terms=serializers.CharField(max_length=16000,trim_whitespace=True)
    warranty_terms=serializers.CharField(max_length=16000,trim_whitespace=True)
    def validate(self,attrs):
        if len(attrs["service_terms"])<30 or len(attrs["warranty_terms"])<30:
            raise serializers.ValidationError("Условия обслуживания и гарантии должны быть содержательными (не менее 30 символов).")
        return attrs

def result(p):
    return {"id":str(p.pk),"version":p.version,"service_terms":p.service_terms,
            "warranty_terms":p.warranty_terms,"created_at":p.created_at.isoformat(),
            "is_current":p.is_current}

class ServicePolicies(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        items=ServicePolicy.objects.filter(organization=self.scope.organization).order_by("-version")[:50]
        return Response([result(p) for p in items])
    def post(self,request):
        require_roles(self.scope,*EDIT)
        data=PolicyPayload(data=request.data);data.is_valid(raise_exception=True)
        def issue():
            current=ServicePolicy.objects.filter(organization=self.scope.organization,is_current=True).first()
            if current and current.service_terms==data.validated_data["service_terms"] and current.warranty_terms==data.validated_data["warranty_terms"]:
                raise BusinessConflict("Такая редакция условий уже действует.")
            version=1+(current.version if current else 0)
            if current:
                current.is_current=False;current.save(update_fields=["is_current"])
            policy=ServicePolicy.objects.create(organization=self.scope.organization,version=version,
                created_by=request.user,**data.validated_data)
            from identity.models import AuditEvent
            AuditEvent.objects.create(organization=self.scope.organization,actor=request.user,
                event_type="service_policy.published",subject_id=policy.pk,details={"version":version})
            return result(policy),201
        body,status=execute_command(request,self.scope,"service_policy.publish",issue)
        return Response(body,status=status)
