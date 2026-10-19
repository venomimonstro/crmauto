from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Branch, Membership, Organization, User


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=12, max_length=128)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Учётная запись уже существует.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name")
        read_only_fields = ("id",)


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("id", "name", "code", "is_active")
        read_only_fields = ("id", "is_active")


class MembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "organization_id", "email", "role", "is_active")
        read_only_fields = fields
