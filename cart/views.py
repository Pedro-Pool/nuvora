from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import CartItem, Cart
from cart.serializers import CartSerializer
from products.models import Product


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

class CartItemAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        if product_id is None:
            return Response({'error': 'Product id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return Response({'error': 'Quantity must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity < 1:
            return Response({'error': 'Quantity must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(
            Product,
            pk=product_id,
            is_active=True,
        )
        cart, _ = Cart.objects.get_or_create(user=request.user)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity},
        )
        if not created:
            item.quantity += quantity

        if item.quantity > product.stock:
            return Response({'error': 'Quantity exceeds stock'}, status=status.HTTP_400_BAD_REQUEST)

        if not created:
            item.save(update_fields=['quantity'])
            cart.save(update_fields=["updated_at"])

        return Response(CartSerializer(cart).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)

        item = get_object_or_404(CartItem, pk=item_id, cart=cart)

        quantity = request.data.get('quantity')

        if quantity is None:
            return Response({'error': 'Quantity is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return Response({'error': 'Quantity must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity < 1:
            return Response({'error': 'Quantity must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity > item.product.stock:
            return Response({'error': 'Quantity exceeds stock'}, status=status.HTTP_400_BAD_REQUEST)

        item.quantity = quantity
        item.save(update_fields=['quantity'])
        cart.save(update_fields=["updated_at"])

        return Response(CartSerializer(cart).data)

    def delete(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        item.delete()
        cart.save(update_fields=["updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)