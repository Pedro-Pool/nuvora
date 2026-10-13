from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import NotFound, ValidationError

from .models import Product
from .serializers import ProductSerializer
from stores.models import Store

class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        return Product.objects.filter(is_active=True).order_by('-created_at')

    def perform_create(self, serializer):
        try:
            store = Store.objects.get(owner=self.request.user)
        except Store.DoesNotExist:
            raise NotFound("Store does not exist")

        serializer.save(store=store)

class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Product.objects.filter(is_active=True)