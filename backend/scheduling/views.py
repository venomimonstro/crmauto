from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from core.commands import execute_command, BusinessConflict
from crm.models import Customer, Vehicle
from identity.models import Branch, AuditEvent, Membership, Organization
from identity.scope import TenantAPIView, require_roles
from .models import ServiceBay, Appointment, Visit
from .serializers import BaySerializer, AppointmentSerializer, VisitSerializer

WRITERS = (Membership.Roles.OWNER, Membership.Roles.MANAGER, Membership.Roles.ADVISER)
READERS = WRITERS + (Membership.Roles.MECHANIC, Membership.Roles.VIEWER)

def audited(scope, user, action, obj):
    AuditEvent.objects.create(organization=scope.organization, actor=user,
                              event_type=action, subject_id=obj.id)

def valid_branch(scope, branch_id):
    branch = get_object_or_404(Branch, id=branch_id, organization_id=scope.organization_id, is_active=True)
    if scope.branch and branch.id != scope.branch.id:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Выбран другой филиал.")
    if scope.membership.role not in (Membership.Roles.OWNER, Membership.Roles.MANAGER):
        from identity.models import MemberBranch
        if not MemberBranch.objects.filter(membership=scope.membership, branch=branch).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Нет допуска к филиалу.")
    return branch

def slot_available(org, branch, bay, start, end, omit=None):
    if bay is None:
        return
    qs = Appointment.objects.filter(organization=org, branch=branch, bay=bay,
        start_at__lt=end, end_at__gt=start,
        status__in=[Appointment.Status.BOOKED, Appointment.Status.CONFIRMED, Appointment.Status.ARRIVED])
    if omit:
        qs = qs.exclude(pk=omit)
    if qs.exists():
        raise BusinessConflict("Пост занят в выбранный период.")

class BaysView(TenantAPIView):
    def get(self, request):
        require_roles(self.scope, *READERS)
        branch = valid_branch(self.scope, request.query_params.get("branch_id"))
        return Response(BaySerializer(ServiceBay.objects.filter(
            organization=self.scope.organization, branch=branch).order_by("name"), many=True).data)

    def post(self, request):
        require_roles(self.scope, *WRITERS)
        def create():
            branch = valid_branch(self.scope, request.data.get("branch_id"))
            serializer = BaySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            bay = serializer.save(organization=self.scope.organization, branch=branch)
            audited(self.scope, request.user, "bay.created", bay)
            return BaySerializer(bay).data, status.HTTP_201_CREATED
        body, code = execute_command(request, self.scope, "bay.create", create)
        return Response(body, status=code)

class AppointmentsView(TenantAPIView):
    def get(self, request):
        require_roles(self.scope, *READERS)
        branch = valid_branch(self.scope, request.query_params.get("branch_id"))
        qs = Appointment.objects.filter(organization=self.scope.organization,
                                        branch=branch).order_by("start_at")[:200]
        return Response(AppointmentSerializer(qs, many=True).data)

    def post(self, request):
        require_roles(self.scope, *WRITERS)
        def create():
            ser = AppointmentSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            d = ser.validated_data
            branch = valid_branch(self.scope, d["branch_id"])
            customer = get_object_or_404(Customer, pk=d["customer_id"], organization=self.scope.organization, archived_at__isnull=True)
            vehicle = get_object_or_404(Vehicle, pk=d["vehicle_id"], organization=self.scope.organization)
            bay = None
            if d.get("bay_id"):
                bay = get_object_or_404(ServiceBay, pk=d["bay_id"], branch=branch,
                                       organization=self.scope.organization, active=True)
            # execute_command locks organization row: serializes all booking decisions for tenant.
            slot_available(self.scope.organization, branch, bay, d["start_at"], d["end_at"])
            appointment = Appointment.objects.create(
                organization=self.scope.organization, branch=branch, customer=customer, vehicle=vehicle,
                bay=bay, start_at=d["start_at"], end_at=d["end_at"],
                description=d.get("description", ""),
            )
            audited(self.scope, request.user, "appointment.created", appointment)
            return AppointmentSerializer(appointment).data, status.HTTP_201_CREATED
        body, code = execute_command(request, self.scope, "appointment.create", create)
        return Response(body, status=code)

class AppointmentActions(TenantAPIView):
    def post(self, request, pk, action):
        require_roles(self.scope, *WRITERS)
        actions = {
            "confirm": ({Appointment.Status.BOOKED}, Appointment.Status.CONFIRMED),
            "cancel": ({Appointment.Status.BOOKED, Appointment.Status.CONFIRMED}, Appointment.Status.CANCELLED),
            "no-show": ({Appointment.Status.BOOKED, Appointment.Status.CONFIRMED}, Appointment.Status.NO_SHOW),
            "arrive": ({Appointment.Status.BOOKED, Appointment.Status.CONFIRMED}, Appointment.Status.ARRIVED),
        }
        if action not in actions:
            raise ValidationError({"action": "Неизвестный переход."})
        def perform():
            obj = get_object_or_404(Appointment.objects.select_for_update(), pk=pk,
                                    organization=self.scope.organization)
            valid_branch(self.scope, obj.branch_id)
            allowed, target = actions[action]
            if obj.status not in allowed:
                raise BusinessConflict("Переход из текущего состояния запрещён.")
            obj.status = target
            obj.version += 1
            obj.save(update_fields=["status", "version"])
            visit_id = None
            if action == "arrive":
                visit = Visit.objects.create(
                    organization=self.scope.organization, branch=obj.branch,
                    appointment=obj, customer=obj.customer, vehicle=obj.vehicle)
                visit_id = str(visit.id)
            audited(self.scope, request.user, "appointment."+action, obj)
            return {"id": str(obj.id), "status": obj.status, "version": obj.version, "visit_id": visit_id}, 200
        body, code = execute_command(request, self.scope, "appointment."+action+"."+str(pk), perform)
        return Response(body, status=code)

class VisitsView(TenantAPIView):
    def get(self, request):
        require_roles(self.scope, *READERS)
        branch = valid_branch(self.scope, request.query_params.get("branch_id"))
        qs = Visit.objects.filter(organization=self.scope.organization, branch=branch).order_by("-arrived_at")[:200]
        return Response(VisitSerializer(qs, many=True).data)
