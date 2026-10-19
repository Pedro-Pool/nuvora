from django.urls import path
from .views import ProductListCreateView, ProductDetailView, CategoryListCreateView, CategoryDetailView

urlpatterns = [
    path('',ProductListCreateView.as_view(), name='products-list-create'),
    path('<int:pk>/',ProductDetailView.as_view(), name='products-detail'),
    path('categories/',CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/',CategoryDetailView.as_view(), name='category-detail'),
]