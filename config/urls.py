
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/',include('users.urls')),
    path('api/stores/',include('stores.urls')),
    path('api/products/',include('products.urls')),
    path('api/categories/',include('products.category_urls')),
    path('api/cart/',include('cart.urls')),
    path('api/orders/',include('orders.urls')),
]
