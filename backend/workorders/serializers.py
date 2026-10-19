from rest_framework import serializers
from .models import WorkOrder,Estimate,EstimateLine

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model=WorkOrder
        fields=("id","branch_id","visit_id","customer_id","vehicle_id","status","complaint",
                "odometer_km","existing_damage","version","created_at")
        read_only_fields=fields

class OrderCreateSerializer(serializers.Serializer):
    visit_id=serializers.UUIDField()
    complaint=serializers.CharField(required=False,allow_blank=True,max_length=3000)
    odometer_km=serializers.IntegerField(required=False,min_value=0,max_value=10000000)
    existing_damage=serializers.CharField(required=False,allow_blank=True,max_length=3000)

class LineWriteSerializer(serializers.Serializer):
    kind=serializers.ChoiceField(choices=EstimateLine.Kind.choices)
    title=serializers.CharField(max_length=200,allow_blank=False)
    quantity=serializers.DecimalField(max_digits=12,decimal_places=3,min_value=0.001)
    unit_price_minor=serializers.IntegerField(min_value=0,max_value=10**12)

class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model=EstimateLine
        fields=("id","kind","title","quantity","unit_price_minor","total_minor")

class EstimateSerializer(serializers.ModelSerializer):
    lines=LineSerializer(many=True,read_only=True)
    class Meta:
        model=Estimate
        fields=("id","revision","state","total_minor","currency","approved_at","approval_method","approval_reference","lines")
