from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError

from .models import Store
from .serializers import StoreSerializer

class StoreCreateView(generics.CreateAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if Store.objects.filter(owner=self.request.user).exists():
            raise ValidationError({"detail":"You already have a store."})
        serializer.save(owner=self.request.user)

class MyStoreView(generics.RetrieveAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return Store.objects.get(owner=self.request.user)
        except Store.DoesNotExist:
            raise NotFound("You do not have a store yet.")
