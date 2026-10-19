"""One-time verified employee invitations.

The invitation URL alone never authenticates a new person. A previously
email-verified, logged-in account with the exact invited email must accept.
"""
from datetime import timedelta
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.access import may_write
from billing.models import Subscription
from core.commands import BusinessConflict, execute_command
from identity.models import AuditEvent, Branch, MemberBranch, Membership, Organization, StaffInvitation
from identity.scope import TenantAPIView, require_roles

SALT = "crmauto-staff-invite-v1"
INVITE_DAYS = 7
INVITER_ROLES = (Membership.Roles.OWNER, Membership.Roles.MANAGER)
ALLOWED_ROLES = (
    Membership.Roles.MANAGER, Membership.Roles.ADVISER, Membership.Roles.MECHANIC,
    Membership.Roles.STOCK, Membership.Roles.CASHIER, Membership.Roles.VIEWER,
)


class InvitePayload(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    role = serializers.ChoiceField(choices=ALLOWED_ROLES)
    branch_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        return value.strip().lower()


class AcceptPayload(serializers.Serializer):
    token = serializers.CharField(max_length=1200)


class EmailDeliveryUnavailable(APIException):
    status_code = 503
    default_detail = "Не удалось отправить приглашение. Повторите позднее."
    default_code = "mail_unavailable"


def invitation_link(invite):
    token = signing.dumps({"invite": str(invite.pk)}, salt=SALT, compress=False)
    return settings.PUBLIC_WEB_ORIGIN + "/?" + urlencode({"staff_invite": token})


def active_invites(organization_id):
    return StaffInvitation.objects.filter(
        organization_id=organization_id,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    )


class StaffInvitations(TenantAPIView):
    def get(self, request):
        require_roles(self.scope, *INVITER_ROLES)
        pending = active_invites(self.scope.organization_id).order_by("-created_at")[:100]
        return Response([{
            "id": str(x.id), "email": x.email, "role": x.role,
            "branch_id": str(x.branch_id) if x.branch_id else None,
            "expires_at": x.expires_at.isoformat(),
        } for x in pending])

    def post(self, request):
        require_roles(self.scope, *INVITER_ROLES)
        if not settings.ENABLE_EMAIL_ONBOARDING:
            raise EmailDeliveryUnavailable("Для приглашений требуется настроенная отправка писем.")

        def issue():
            payload = InvitePayload(data=request.data)
            payload.is_valid(raise_exception=True)
            data = payload.validated_data
            org = Organization.objects.select_for_update().get(pk=self.scope.organization_id)
            role = data["role"]
            if role == Membership.Roles.MANAGER and self.scope.membership.role != Membership.Roles.OWNER:
                raise PermissionDenied("Назначить управляющего может только владелец.")
            branch = None
            if role not in (Membership.Roles.OWNER, Membership.Roles.MANAGER):
                if not data.get("branch_id"):
                    raise ValidationError({"branch_id": "Укажите филиал сотрудника."})
                branch = get_object_or_404(Branch, pk=data["branch_id"],
                    organization=org, is_active=True)
            sub = get_object_or_404(Subscription.objects.select_related("plan"),
                                    organization=org)
            current_count = Membership.objects.filter(organization=org, is_active=True).count()
            pending_count = active_invites(org.pk).count()
            if current_count + pending_count >= sub.plan.max_staff:
                raise BusinessConflict("Достигнут лимит сотрудников тарифа.")
            if Membership.objects.filter(organization=org,
                    user__email__iexact=data["email"], is_active=True).exists():
                raise BusinessConflict("Пользователь уже состоит в компании.")
            if active_invites(org.pk).filter(email__iexact=data["email"]).exists():
                raise BusinessConflict("Активное приглашение на этот адрес уже существует.")
            invite = StaffInvitation.objects.create(
                organization=org, branch=branch, email=data["email"], role=role,
                invited_by=request.user, expires_at=timezone.now()+timedelta(days=INVITE_DAYS))
            try:
                sent = send_mail(
                    "Приглашение в CRM автосервиса",
                    "Вас пригласили в рабочую организацию: " + org.name
                    + "\nВойдите в собственную подтверждённую учётную запись и примите приглашение:\n"
                    + invitation_link(invite) + "\nСрок действия: 7 дней.",
                    settings.DEFAULT_FROM_EMAIL, [invite.email], fail_silently=False,
                )
            except Exception as exc:
                raise EmailDeliveryUnavailable() from exc
            if sent != 1:
                raise EmailDeliveryUnavailable()
            AuditEvent.objects.create(organization=org,actor=request.user,
                event_type="staff.invited", subject_id=invite.pk)
            return {"id": str(invite.pk), "expires_at": invite.expires_at.isoformat()}, 201

        body, code = execute_command(request, self.scope, "staff.invite", issue)
        return Response(body, status=code)


class AcceptStaffInvitation(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        payload = AcceptPayload(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            data = signing.loads(payload.validated_data["token"], salt=SALT,
                                 max_age=INVITE_DAYS * 24 * 3600)
            invite_id = UUID(data["invite"])
        except (signing.BadSignature, signing.SignatureExpired, ValueError,
                TypeError, KeyError, AttributeError):
            raise ValidationError({"token": "Приглашение недействительно или истекло."})
        invite = get_object_or_404(StaffInvitation.objects.select_related(
            "organization", "branch"), pk=invite_id)
        Organization.objects.select_for_update().get(pk=invite.organization_id)
        invite = StaffInvitation.objects.select_for_update().get(pk=invite.pk)
        now = timezone.now()
        if (invite.accepted_at or invite.revoked_at or invite.expires_at <= now
                or not invite.organization.is_active):
            raise BusinessConflict("Приглашение больше не действует.")
        if not request.user.is_active or request.user.email.strip().lower() != invite.email.lower():
            raise PermissionDenied("Войдите в подтверждённую учётную запись указанного адреса.")
        if settings.BILLING_ENFORCE_WRITES and not may_write(invite.organization_id):
            raise PermissionDenied("Доступ к компании по тарифу временно ограничен.")
        subscription = get_object_or_404(Subscription.objects.select_related("plan"),
                                         organization=invite.organization)
        count = Membership.objects.filter(organization=invite.organization, is_active=True).count()
        if count >= subscription.plan.max_staff:
            raise BusinessConflict("У организации закончились места для сотрудников.")
        if Membership.objects.filter(organization=invite.organization,
                                      user=request.user).exists():
            raise BusinessConflict("Учётная запись уже связана с организацией.")
        if invite.role not in ALLOWED_ROLES:
            raise PermissionDenied("Недопустимая роль приглашения.")
        if invite.role not in (Membership.Roles.OWNER, Membership.Roles.MANAGER):
            if not invite.branch_id or not Branch.objects.filter(
                    pk=invite.branch_id, organization=invite.organization, is_active=True).exists():
                raise BusinessConflict("Филиал сотрудника больше не доступен.")
        member = Membership.objects.create(
            organization=invite.organization, user=request.user, role=invite.role)
        if invite.branch_id and invite.role not in (Membership.Roles.OWNER, Membership.Roles.MANAGER):
            MemberBranch.objects.create(membership=member, branch_id=invite.branch_id)
        invite.accepted_at = now
        invite.save(update_fields=["accepted_at"])
        AuditEvent.objects.create(organization=invite.organization,actor=request.user,
            event_type="staff.accepted",subject_id=member.pk)
        return Response({"organization_id": str(invite.organization_id),
                         "membership_id": str(member.pk), "role": member.role}, status=201)
