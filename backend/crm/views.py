from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.commands import BusinessConflict, execute_command
from identity.models import AuditEvent, Membership
from identity.scope import TenantAPIView, require_roles
from .models import Customer, Ownership, Vehicle
from .serializers import CustomerSerializer, OwnershipSerializer, VehicleSerializer, digits
from .importer import parse_csv

EDITORS = (Membership.Roles.OWNER, Membership.Roles.MANAGER, Membership.Roles.ADVISER)
READERS = EDITORS + (Membership.Roles.VIEWER,)
VEHICLE_READERS = READERS + (Membership.Roles.MECHANIC, Membership.Roles.STOCK)


def audit(scope, user, kind, obj):
    AuditEvent.objects.create(organization=scope.organization, actor=user,
                              event_type=kind, subject_id=obj.id)


class CustomerList(TenantAPIView):
    def get(self, request):
        require_roles(self.scope, *READERS)
        qs = Customer.objects.filter(organization_id=self.scope.organization_id, archived_at__isnull=True)
        q = request.query_params.get("q", "").strip()[:100]
        if q:
            # Empty digits should not match all rows.
            match = Q(name__icontains=q)
            if digits(q):
                match |= Q(phone_digits__icontains=digits(q))
            qs = qs.filter(match)
        return Response(CustomerSerializer(qs.order_by("name")[:100], many=True).data)

    def post(self, request):
        require_roles(self.scope, *EDITORS)

        def create():
            ser = CustomerSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            obj = ser.save(organization=self.scope.organization,
                           phone_digits=digits(ser.validated_data.get("phone", "")))
            audit(self.scope, request.user, "customer.created", obj)
            return CustomerSerializer(obj).data, status.HTTP_201_CREATED

        body, code = execute_command(request, self.scope, "customer.create", create)
        return Response(body, status=code)


class CustomerDetail(TenantAPIView):
    def get(self, request, pk):
        require_roles(self.scope, *READERS)
        customer = get_object_or_404(Customer, pk=pk, organization_id=self.scope.organization_id)
        return Response(CustomerSerializer(customer).data)

    @transaction.atomic
    def patch(self, request, pk):
        require_roles(self.scope, *EDITORS)
        customer = get_object_or_404(Customer.objects.select_for_update(), pk=pk,
                                     organization_id=self.scope.organization_id)
        try:
            expected = int(request.headers.get("If-Match", ""))
        except (ValueError, TypeError):
            raise ValidationError({"If-Match": "Укажите версию изменяемой карточки."})
        if customer.version != expected:
            raise BusinessConflict("Карточка уже изменена другим пользователем.")
        ser = CustomerSerializer(customer, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        obj = ser.save(version=customer.version + 1,
                       phone_digits=digits(ser.validated_data.get("phone", customer.phone)))
        audit(self.scope, request.user, "customer.updated", obj)
        return Response(CustomerSerializer(obj).data)


class VehicleList(TenantAPIView):
    def get(self, request):
        require_roles(self.scope, *VEHICLE_READERS)
        qs = Vehicle.objects.filter(organization_id=self.scope.organization_id)
        q = request.query_params.get("q", "").strip()[:100]
        if q:
            qs = qs.filter(Q(vin__icontains=q) | Q(plate__icontains=q) |
                           Q(make__icontains=q) | Q(model__icontains=q))
        payload = VehicleSerializer(qs.order_by("-created_at")[:100], many=True).data
        if self.scope.membership.role not in READERS:
            for item in payload:
                item.pop("current_owner", None)
        return Response(payload)

    def post(self, request):
        require_roles(self.scope, *EDITORS)

        def create():
            ser = VehicleSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            owner = None
            if request.data.get("owner_id"):
                owner = get_object_or_404(Customer, pk=request.data["owner_id"],
                                          organization_id=self.scope.organization_id, archived_at__isnull=True)
            try:
                with transaction.atomic():
                    car = ser.save(organization=self.scope.organization)
                    if owner:
                        Ownership.objects.create(organization=self.scope.organization,
                                                 vehicle=car, customer=owner)
            except IntegrityError as e:
                raise BusinessConflict("Автомобиль с таким VIN уже внесён.") from e
            audit(self.scope, request.user, "vehicle.created", car)
            return VehicleSerializer(car).data, status.HTTP_201_CREATED

        body, code = execute_command(request, self.scope, "vehicle.create", create)
        return Response(body, status=code)


class VehicleDetail(TenantAPIView):
    def get(self, request, pk):
        require_roles(self.scope, *VEHICLE_READERS)
        car = get_object_or_404(Vehicle, pk=pk, organization_id=self.scope.organization_id)
        data = VehicleSerializer(car).data
        # A mechanic/stock role never receives even the owner's UUID.
        if self.scope.membership.role not in READERS:
            data.pop("current_owner", None)
        # A mechanic can view a car but not the full identity history.
        if self.scope.membership.role in READERS:
            data["owners_history"] = OwnershipSerializer(car.ownerships.order_by("created_at"), many=True).data
        return Response(data)


class VehicleTransfer(TenantAPIView):
    def post(self, request, pk):
        require_roles(self.scope, *EDITORS)

        def transfer():
            car = get_object_or_404(Vehicle.objects.select_for_update(), pk=pk,
                                    organization_id=self.scope.organization_id)
            customer = get_object_or_404(Customer, pk=request.data.get("customer_id"),
                                         organization_id=self.scope.organization_id, archived_at__isnull=True)
            current = Ownership.objects.select_for_update().filter(vehicle=car, ended_on__isnull=True).first()
            if current and current.customer_id == customer.id:
                raise BusinessConflict("Клиент уже является владельцем автомобиля.")
            date = timezone.localdate()
            if current:
                current.ended_on = date
                current.save(update_fields=["ended_on"])
            row = Ownership.objects.create(organization=self.scope.organization, vehicle=car,
                                           customer=customer, started_on=date)
            car.version += 1
            car.save(update_fields=["version", "updated_at"])
            audit(self.scope, request.user, "vehicle.owner_changed", car)
            return {"id": str(car.id), "owner": str(customer.id),
                    "ownership_record": str(row.id), "version": car.version}, 200

        body, code = execute_command(request, self.scope, "vehicle.owner_change", transfer)
        return Response(body, status=code)


class Search(TenantAPIView):
    def get(self, request):
        require_roles(self.scope, *VEHICLE_READERS)
        q = request.query_params.get("q", "").strip()[:100]
        if len(q) < 2:
            return Response({"customers": [], "vehicles": []})
        v = Vehicle.objects.filter(organization_id=self.scope.organization_id).filter(
            Q(vin__icontains=q) | Q(plate__icontains=q) | Q(make__icontains=q)
        ).order_by("-created_at")[:20]
        vehicle_rows = VehicleSerializer(v, many=True).data
        if self.scope.membership.role not in READERS:
            for item in vehicle_rows:
                item.pop("current_owner", None)
        result = {"vehicles": vehicle_rows, "customers": []}
        if self.scope.membership.role in READERS:
            match = Q(name__icontains=q)
            if digits(q):
                match |= Q(phone_digits__icontains=digits(q))
            c = Customer.objects.filter(organization_id=self.scope.organization_id).filter(match)[:20]
            result["customers"] = CustomerSerializer(c, many=True).data
        return Response(result)


class ImportPreview(TenantAPIView):
    def post(self, request):
        require_roles(self.scope, *EDITORS)
        result = parse_csv(request.data.get("csv"), self.scope.organization)
        # Preview never changes persisted data.
        return Response(result)


class ImportApply(TenantAPIView):
    def post(self, request):
        require_roles(self.scope, *EDITORS)

        def commit():
            result = parse_csv(request.data.get("csv"), self.scope.organization)
            if result["errors"]:
                raise ValidationError({"csv": "Импорт отклонён целиком. Исправьте строки.",
                                       "rows": result["errors"]})
            created = 0
            for row in result["entries"]:
                if row["action"] != "create":
                    continue
                ser = CustomerSerializer(data=row["data"])
                ser.is_valid(raise_exception=True)
                ser.save(organization=self.scope.organization,
                         phone_digits=digits(ser.validated_data.get("phone", "")))
                created += 1
            audit_id = self.scope.organization_id
            AuditEvent.objects.create(
                organization=self.scope.organization, actor=request.user,
                event_type="customer.csv_imported", subject_id=audit_id,
                details={"created": created, "skipped": result["skip_count"]},
            )
            return {"created": created, "skipped": result["skip_count"]}, status.HTTP_201_CREATED

        body, code = execute_command(request, self.scope, "customer.csv_import", commit)
        return Response(body, status=code)
