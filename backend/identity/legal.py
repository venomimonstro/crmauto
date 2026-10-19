"""Tenant-owned business details for workshop paperwork; not proof of registration."""
from rest_framework import serializers
import re
from rest_framework.response import Response
from identity.models import Membership, OrganizationLegalProfile
from identity.scope import TenantAPIView,require_roles
from core.commands import execute_command

READ=(Membership.Roles.OWNER,Membership.Roles.MANAGER,Membership.Roles.ADVISER,Membership.Roles.VIEWER)
EDIT=(Membership.Roles.OWNER,Membership.Roles.MANAGER)

class ProfileData(serializers.ModelSerializer):
    class Meta:
        model=OrganizationLegalProfile
        fields=("legal_name","entity_kind","inn","kpp","ogrn","postal_address",
                "service_address","phone","email","bank_name","bik",
                "account_number","correspondent_account","tax_label","version")
        read_only_fields=("version",)
    def validate(self,data):
        kind=data.get("entity_kind",getattr(self.instance,"entity_kind","company"))
        for field, lengths in (("inn",(10,12)),("kpp",(9,)),("ogrn",(13,15)),
                                ("bik",(9,)),("account_number",(20,)),
                                ("correspondent_account",(20,))):
            raw=data.get(field,getattr(self.instance,field,""))
            if raw and (not re.fullmatch(r"[0-9]+",raw) or len(raw) not in lengths):
                raise serializers.ValidationError({field:"Проверьте количество цифр и формат реквизита."})
        inn=data.get("inn",getattr(self.instance,"inn",""))
        if inn and ((kind=="company" and len(inn)!=10) or (kind in ("individual","self_employed") and len(inn)!=12)):
            raise serializers.ValidationError({"inn":"Длина ИНН не соответствует типу исполнителя."})
        if kind=="self_employed" and data.get("kpp",getattr(self.instance,"kpp","")):
            raise serializers.ValidationError({"kpp":"Самозанятому не нужен КПП."})
        return data


class LegalProfile(TenantAPIView):
    def get(self,request):
        require_roles(self.scope,*READ)
        profile,_=OrganizationLegalProfile.objects.get_or_create(organization=self.scope.organization)
        return Response(ProfileData(profile).data)
    def patch(self,request):
        require_roles(self.scope,*EDIT)
        def update():
            profile,_=OrganizationLegalProfile.objects.select_for_update().get_or_create(
                organization=self.scope.organization)
            try: expected=int(request.headers.get("If-Match",""))
            except (ValueError,TypeError):
                raise serializers.ValidationError({"If-Match":"Укажите версию реквизитов."})
            if expected!=profile.version:
                from core.commands import BusinessConflict
                raise BusinessConflict("Реквизиты изменены другим сотрудником. Обновите форму.")
            serializer=ProfileData(profile,data=request.data,partial=True)
            serializer.is_valid(raise_exception=True)
            instance=serializer.save(version=profile.version+1)
            from identity.models import AuditEvent
            AuditEvent.objects.create(organization=self.scope.organization,actor=request.user,
                event_type="legal_profile.updated",subject_id=self.scope.organization_id,
                details={"version":instance.version})
            return ProfileData(instance).data,200
        body,status=execute_command(request,self.scope,"legal_profile.update",update)
        return Response(body,status=status)
