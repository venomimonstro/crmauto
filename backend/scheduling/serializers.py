from rest_framework import serializers
from .models import ServiceBay, Appointment, Visit

class BaySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceBay
        fields = ("id", "name", "active")
        read_only_fields = ("id", "active")

class AppointmentSerializer(serializers.ModelSerializer):
    branch_id = serializers.UUIDField(write_only=True)
    customer_id = serializers.UUIDField(write_only=True)
    vehicle_id = serializers.UUIDField(write_only=True)
    bay_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    class Meta:
        model = Appointment
        fields = ("id", "branch_id", "customer_id", "vehicle_id", "bay_id", "start_at", "end_at", "status", "description", "version")
        read_only_fields = ("id", "status", "version")

    def validate(self, attrs):
        if attrs["end_at"] <= attrs["start_at"]:
            raise serializers.ValidationError({"end_at": "Окончание должно быть позже начала."})
        if (attrs["end_at"] - attrs["start_at"]).total_seconds() > 24*3600:
            raise serializers.ValidationError({"end_at": "Одна запись не может превышать 24 часа."})
        return attrs

class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ("id", "appointment_id", "branch_id", "customer_id", "vehicle_id", "arrived_at", "status")
