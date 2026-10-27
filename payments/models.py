import uuid

from django.db import models
from django.db.models import Q
from orders.models import Order


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    class Provider(models.TextChoices):
        ASAAS = 'asaas', 'Asaas'
        MANUAL = 'manual', 'Manual'

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='payments')
    reference = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    provider = models.CharField(choices=Provider.choices, max_length=20, default=Provider.MANUAL)
    status = models.CharField(choices=Status.choices, max_length=20, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="BRL")
    provider_payment_id = models.CharField(max_length=255, blank=True)
    provider_checkout_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order'],
                condition=Q(status='pending'),
                name='unique_pending_payment_per_order',
            )
        ]

    def __str__(self):
        return f'Payment {self.reference} - {self.status}'
