from rest_framework import serializers
from .models import Warehouse,Part,Stock,Reservation,Movement
class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model=Warehouse
        fields=("id","branch_id","name","active")
        read_only_fields=("id","active")
class PartSerializer(serializers.ModelSerializer):
    class Meta:
        model=Part
        fields=("id","sku","name","condition")
        read_only_fields=("id",)
class StockSerializer(serializers.ModelSerializer):
    available=serializers.SerializerMethodField()
    class Meta:
        model=Stock
        fields=("id","warehouse_id","part_id","quantity","reserved","available")
    def get_available(self,obj):
        return obj.quantity-obj.reserved
class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model=Reservation
        fields=("id","stock_id","order_id","quantity","state")
