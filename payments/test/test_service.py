from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from payments.models import Payment
from payments.service import AsaasError, create_asaas_checkout

@override_settings(
    ASAAS_API_KEY="test_api_key",
    ASAAS_BASE_URL="https://api-sandbox.asaas.com/v3",
    ASAAS_SUCCESS_URL="http://localhost:8000/api/payments/checkout/success/",
    ASAAS_CANCEL_URL="http://localhost:8000/api/payments/checkout/canceled/",
    ASAAS_EXCEPTION_URL="http://localhost:8000/api/payments/checkout/expired/",
)
class CreateAsaasCheckoutTest(SimpleTestCase):
    def setUp(self):
        self.payment = Mock()
        self.payment.reference = 'test-payment=reference'
        self.payment.amount = Decimal("50.00")
        self.payment.Provider = Payment.Provider
        self.payment.provider = Payment.Provider.MANUAL
        self.payment.order.items.all.return_value = [
            Mock(
                product_name="Test Product",
                quantity=2,
                unit_price=Decimal("25.00"),
            )
        ]
    @patch('payments.service.requests.post')
    def test_01(self, mock_post):
        """Create checkout success"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id":"chk_test123",
            "link":"https://sandbox.asaas.com/checkout/test123",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = create_asaas_checkout(payment=self.payment)

        self.assertEqual(result["checkout_id"], "chk_test123")
        self.assertEqual(result["checkout_url"], "https://sandbox.asaas.com/checkout/test123")

        self.assertEqual(self.payment.provider, Payment.Provider.ASAAS)
        self.assertEqual(self.payment.provider_checkout_id, "chk_test123")
        self.payment.save.assert_called_once()

        __, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["billingTypes"], ["PIX", "CREDIT_CARD"])
        self.assertEqual(kwargs["json"]["items"][0]["value"], 25.00)
        self.assertEqual(kwargs["timeout"], 15)

    @patch('payments.service.requests.post')
    def test_02(self, mock_post):
        """http error raises asaas error"""
        import requests

        mock_post.return_value.raise_for_status.side_effect = (requests.HTTPError("HTTP 400"))

        with self.assertRaises(AsaasError):
            create_asaas_checkout(self.payment)

    @patch('payments.service.requests.post')
    def test_03(self, mock_post):
        """invalid json raises asaas error"""

        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.side_effect = ValueError("invalid json")

        with self.assertRaises(AsaasError):
            create_asaas_checkout(self.payment)

    @patch('payments.service.requests.post')
    def test_04(self, mock_post):
        """missing checkout fields raises asaas error"""

        mock_response = Mock()
        mock_response.return_value.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "link":"https://example.com/checkout",
        }
        mock_post.return_value = mock_response

        with self.assertRaises(AsaasError):
            create_asaas_checkout(self.payment)

    @override_settings(ASAAS_API_KEY="")
    def test_05(self):
        """missing api key raises asaas error"""

        with self.assertRaises(AsaasError):
            create_asaas_checkout(self.payment)

    def test_06(self):
        """order without items raises asaas error"""

        self.payment.order.items.all.return_value = []

        with self.assertRaises(AsaasError):
            create_asaas_checkout(self.payment)
