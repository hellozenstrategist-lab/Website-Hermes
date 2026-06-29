import os
import unittest
from unittest import mock

from ops_cfo.engine import StripeGateway, StaticStripeGateway


class StripeGatewayTests(unittest.TestCase):
    def test_from_env_without_key_uses_static_demo_gateway(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            gateway = StripeGateway.from_env()
        self.assertIsInstance(gateway, StaticStripeGateway)
        link = gateway.create_payment_link("AI Security Review", 499)
        self.assertEqual(link["url"], "https://stripe.test/pay/ai-security-review-499")
        self.assertEqual(link["mode"], "demo")

    def test_from_env_rejects_live_secret_keys(self):
        with mock.patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_live_deadbeef"}, clear=True):
            with self.assertRaisesRegex(ValueError, "Refusing live Stripe key"):
                StripeGateway.from_env()

    def test_static_gateway_slugifies_product_name(self):
        gateway = StaticStripeGateway(base_url="https://stripe.test")
        link = gateway.create_payment_link("GPU Inference Credits!", 200)
        self.assertEqual(link["url"], "https://stripe.test/pay/gpu-inference-credits-200")


if __name__ == "__main__":
    unittest.main()
