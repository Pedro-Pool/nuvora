from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            'id',
            'store',
            'category',
            'name',
            'description',
            'price',
            'stock',
            'is_active',
            'created_at',
        )
        read_only_fields = ('id', 'store', 'is_active', 'created_at')