from decimal import Decimal
from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from orders.serializers import OrderSerializer
from products.models import Product


class OrderCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        orders = (Order.objects.filter(user=request.user).prefetch_related("items").order_by("-created_at"))

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        with transaction.atomic():
            cart = Cart.objects.filter(user=request.user).first()

            if cart is None:
                return Response({"detail":"Cart not found"}, status=status.HTTP_404_NOT_FOUND)

            cart_item = CartItem.objects.filter(cart=cart).order_by('product_id')

            if not cart_item:
                return Response(
                    {"detail":"It is not possible to create an order with an empty cart"},
                    status=status.HTTP_400_BAD_REQUEST)

            products = {}

            for item in cart_item:
                try:
                    product = (Product.objects.select_for_update().get(pk=item.product_id))
                except Product.DoesNotExist:
                    return Response(
                    {"detail":"One of the items in your cart no longer exists"}, status=status.HTTP_400_BAD_REQUEST
                    )
                if not product.is_active:
                    return Response(
                        {"detail": f"The product {product.name} is not available."}, status=status.HTTP_400_BAD_REQUEST
                    )
                if item.quantity > product.stock:
                    return Response(
                        {"detail":(f"Insufficient stock for {product.name}", f'Available: {product.stock}')},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                products[product.pk] = product

            total = sum((products[item.product_id].price * item.quantity
                        for item in cart_item), Decimal("0.00"))

            order = Order.objects.create(
                user=request.user,
                total_amount=total,
            )

            for item in cart_item:
                product = products[item.product_id]

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=item.quantity,
                )
                product.stock -= item.quantity
                product.save(update_fields=['stock'])

            CartItem.objects.filter(cart=cart).delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

class OrderDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, order_id):
        try:
            order = Order.objects.prefetch_related("items").get(pk=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail":"Order not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrderCanceledView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, order_id):
        with transaction.atomic():
            try:
                order = (Order.objects.select_for_update().get(pk=order_id, user=request.user))
            except Order.DoesNotExist:
                return Response({"detail":"Order not found"}, status=status.HTTP_404_NOT_FOUND)

            allowed_statuses = {
                Order.Status.PENDING,
                Order.Status.CONFIRMED,
                Order.Status.PROCESSING,
            }

            if order.status not in allowed_statuses:
                return Response({"detail":"This order cannot be cancelled"}, status=status.HTTP_400_BAD_REQUEST)

            items = list(order.items.all().order_by("product_id"))

            products = {}

            for item in items:
                try:
                    product = (Product.objects.select_for_update().get(pk=item.product_id))
                except Product.DoesNotExist:
                    return Response({"detail":"A product from this order no longer exists"},
                                    status=status.HTTP_400_BAD_REQUEST)

                products[product.pk] = product

            for item in items:
                product = products[item.product_id]
                product.stock += item.quantity
                product.save(update_fields=['stock'])

            order.status = Order.Status.CANCELED
            order.save(update_fields=['status', 'updated_at'])

        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)