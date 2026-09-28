from unittest.mock import MagicMock, patch

from django.test import (
    SimpleTestCase,
    override_settings,
)

from payments.stripe_client import get_stripe_client


class StripeClientTests(SimpleTestCase):
    @override_settings(STRIPE_SECRET_KEY="sk_test_secret")
    @patch("payments.stripe_client.stripe.StripeClient")
    def test_get_stripe_client_uses_configured_secret_key(
        self,
        mocked_stripe_client_class: MagicMock,
    ) -> None:
        expected_client = MagicMock()
        mocked_stripe_client_class.return_value = expected_client

        result = get_stripe_client()

        self.assertIs(
            result,
            expected_client,
        )
        mocked_stripe_client_class.assert_called_once_with("sk_test_secret")
