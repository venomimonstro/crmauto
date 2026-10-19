from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from .models import AuditEvent, Branch, Membership, Organization, User
from .scope import TenantAPIView, require_roles
from .serializers import BranchSerializer, OrganizationSerializer, RegisterSerializer


class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        data = RegisterSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = User.objects.create_user(**data.validated_data)
        # Email verification must be implemented before open public registration.
        return Response({"id": str(user.pk), "verification_required_before_public_launch": True},
                        status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        email, password = request.data.get("email"), request.data.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            raise ValidationError({"credentials": "Требуются почта и пароль."})
        user = authenticate(request, username=email.strip().lower(), password=password)
        if user is None:
            return Response({"code": "invalid_credentials", "message_ru": "Неверные учётные данные."},
                            status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        request.session.cycle_key()
        return Response({"id": str(user.pk), "email": user.email})


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        ms = Membership.objects.filter(user=request.user, is_active=True, organization__is_active=True).select_related("organization")
        return Response({"id": str(request.user.pk), "email": request.user.email,
                         "organizations": [{"id": str(m.organization_id), "name": m.organization.name, "role": m.role}
                                           for m in ms]})


class OrganizationsView(APIView):
    def get(self, request):
        memberships = Membership.objects.filter(user=request.user, is_active=True, organization__is_active=True).select_related("organization")
        return Response([{"id": str(m.organization_id), "name": m.organization.name, "role": m.role}
                         for m in memberships])

    @transaction.atomic
    def post(self, request):
        data = OrganizationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        org = data.save()
        branch = Branch.objects.create(organization=org, name="Основной", code="main")
        Membership.objects.create(organization=org, user=request.user, role=Membership.Roles.OWNER)
        AuditEvent.objects.create(organization=org, actor=request.user, event_type="organization.created",
                                  subject_id=org.id)
        return Response({"id": str(org.id), "name": org.name, "branch_id": str(branch.id)},
                        status=status.HTTP_201_CREATED)


class BranchesView(TenantAPIView):
    def get(self, request):
        if self.scope.membership.role in (Membership.Roles.OWNER, Membership.Roles.MANAGER):
            branches = Branch.objects.filter(organization_id=self.scope.organization_id)
        else:
            branches = Branch.objects.filter(
                organization_id=self.scope.organization_id,
                memberbranch__membership=self.scope.membership,
            )
        return Response(BranchSerializer(branches.order_by("name"), many=True).data)

    @transaction.atomic
    def post(self, request):
        require_roles(self.scope, Membership.Roles.OWNER, Membership.Roles.MANAGER)
        data = BranchSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        branch = data.save(organization=self.scope.organization)
        AuditEvent.objects.create(organization=self.scope.organization, actor=request.user,
                                  event_type="branch.created", subject_id=branch.id)
        return Response(BranchSerializer(branch).data, status=status.HTTP_201_CREATED)
