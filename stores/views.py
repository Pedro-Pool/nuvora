from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from .models import Store
from .serializers import StoreSerializer

class StoreCreateView(generics.CreateAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class MyStoreView(generics.RetrieveAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return Store.objects.get(user=self.request.user)
        except Store.DoesNotExist:
            raise NotFound("You do not have a store yet.")
