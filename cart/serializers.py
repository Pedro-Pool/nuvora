from rest_framework import serializers

from products.serializers import ProductSerializer
from .models import CartItem, Cart


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = (
            'id',
            'product',
            'quantity',
        )
        read_only_fields = ('id', 'product')

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(read_only=True, many=True)

    class Meta:
        model = Cart
        fields = (
            'id',
            'items',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'items', 'created_at', 'updated_at')