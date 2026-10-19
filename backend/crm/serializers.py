import re
from datetime import date
from rest_framework import serializers
from .models import Customer, Vehicle, Ownership


def digits(s):
    return "".join(c for c in s if c.isdigit())


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "kind", "name", "phone", "email", "notes", "version", "created_at")
        read_only_fields = ("id", "version", "created_at")

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Имя или название от двух символов.")
        return value

    def validate_phone(self, value):
        if value and not 10 <= len(digits(value)) <= 15:
            raise serializers.ValidationError("Телефон: от 10 до 15 цифр.")
        return value


class VehicleSerializer(serializers.ModelSerializer):
    current_owner = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ("id", "vin", "plate", "make", "model", "year", "version", "current_owner", "created_at")
        read_only_fields = ("id", "version", "current_owner", "created_at")

    def validate_vin(self, value):
        vin = value.replace(" ", "").upper()
        if vin and not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin):
            raise serializers.ValidationError("VIN: ровно 17 символов, без I, O и Q.")
        return vin

    def validate_year(self, value):
        if value is not None and not 1886 <= value <= date.today().year + 1:
            raise serializers.ValidationError("Неверный год выпуска.")
        return value

    def get_current_owner(self, vehicle):
        current = vehicle.ownerships.filter(ended_on__isnull=True).first()
        return str(current.customer_id) if current else None


class OwnershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ownership
        fields = ("id", "customer_id", "started_on", "ended_on")
