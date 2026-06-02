from .config import settings
import stripe


stripe.api_key = settings.stripe_secret_key

