from rest_framework import serializers

from orders.models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = (
            'id',
            'product',
            'product_name',
            'unit_price',
            'quantity',
            'subtotal',
        )
        read_only_fields = fields

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id',
            'status',
            'items',
            'total_amount',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields