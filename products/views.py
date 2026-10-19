from decimal import Decimal, InvalidOperation

from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.exceptions import NotFound, ValidationError

from .models import Product, Category, Store
from .serializers import ProductSerializer
from .category_serializers import CategorySerializer

class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name']

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).order_by('-created_at')

        category_id = self.request.query_params.get('category')
        if category_id:
            try:
                category_id = int(category_id)
            except (ValueError, TypeError):
                raise ValidationError({"category": "Enter a valid category ID"})

            queryset = queryset.filter(category_id=category_id)

        min_price = self.request.query_params.get('min_price')
        if min_price is not None:
            try:
                min_price = Decimal(min_price)
                if not min_price.is_finite() or min_price < 0:
                    raise ValueError
            except (ValueError, TypeError, InvalidOperation):
                raise ValidationError({"min_price": "Enter a valid non-negative price"})

            queryset = queryset.filter(price__gte=min_price)

        max_price = self.request.query_params.get('max_price')
        if max_price is not None:
            try:
                max_price = Decimal(max_price)
                if not max_price.is_finite() or max_price < 0:
                    raise ValueError
            except (ValueError, TypeError, InvalidOperation):
                raise ValidationError({"max_price": "Enter a valid non-negative price"})

            queryset = queryset.filter(price__lte=max_price)

        if min_price is not None and max_price is not None:
            if min_price > max_price:
                raise ValidationError({"price": "min_price cannot be greater than max_price"})

        return queryset

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

class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.all().order_by('name')

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [AllowAny()]

class CategoryDetailView(generics.RetrieveAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    permission_classes = [AllowAny]