from rest_framework import serializers
from .models import Store

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = (
            "id",
            "name",
            "description",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "is_active", "created_at")