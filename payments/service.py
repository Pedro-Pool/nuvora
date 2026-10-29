import requests

from django.conf import settings

from .models import Payment

class AsaasError(Exception):
    """Error creating a Checkout in Asaas"""

def create_asaas_checkout(payment):
    if not settings.ASAAS_API_KEY:
        raise AsaasError("The Asaas API key is not configured")

    order = payment.order

    items = []
    for item in order.items.all():
        items.append({
            "name": item.product_name,
            "quantity": item.quantity,
            "value":float(item.unit_price),
        })
    if not items:
        raise AsaasError("It is not possible to create a Checkout for an order with no items")

    payload = {
        "billingTypes": ["PIX", "CREDIT_CARD"],
        "chargeTypes":["DETACHED"],
        "externalReference":str(payment.reference),
        "minutesToExpire":60,
        "callback": {
            "successUrl":settings.ASAAS_SUCCESS_URL,
            "cancelUrl":settings.ASAAS_CANCEL_URL,
            "expiredUrl":settings.ASAAS_EXPIRED_URL,
        },
        "items": items,
    }
    url = f"{settings.ASAAS_BASE_URL.rstrip('/')}/checkouts"

    try:
        response = requests.post(
            url,
            headers={
                "access_token": settings.ASAAS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=15,
        )
        if not response.ok:
            print("Asaas HTTP status:", response.status_code)
            print("Asaas response body:", response.text)

        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise AsaasError("It was not possible to create the Checkout in Asaas") from exc
    except ValueError as exc:
        raise AsaasError("Asaas returned an invalid response") from exc

    checkout_id = data.get("id")

    if not checkout_id:
        raise AsaasError("The response from Asaas does not contain the Checkout identifier.")

    checkout_link = data.get("link")

    if not checkout_link:
        raise AsaasError(
            "The response from Asaas does not contain the Checkout link."
        )

    payment.provider = Payment.Provider.ASAAS
    payment.provider_checkout_id = checkout_id
    payment.save(
        update_fields=["provider", "provider_checkout_id", "updated_at"]
    )
    return {"checkout_id": checkout_id, "checkout_url": checkout_link}
