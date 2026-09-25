class PaymentSessionMismatchError(Exception):
    """Stripe Session does not match the stored payment."""
