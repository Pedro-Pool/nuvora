from django.urls import path
from .views import StoreCreateView, MyStoreView

urlpatterns = [
    path("", StoreCreateView.as_view(), name="store_create"),
    path("me/", MyStoreView.as_view(), name="my_store"),
]