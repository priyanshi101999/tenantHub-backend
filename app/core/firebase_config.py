import json
import logging

from app.core.config import settings
from firebase_admin import get_app, initialize_app
from firebase_admin import credentials


logger = logging.getLogger(__name__)


def initialize_firebase_app():
    try:
        return get_app()
    except ValueError:
        pass

    if settings.firebase_service_account_json:
        cert_info = json.loads(settings.firebase_service_account_json)
        cred = credentials.Certificate(cert_info)
    else:
        cred = credentials.Certificate(settings.firebase_service_account_path)

    app = initialize_app(cred)
    logger.info("Firebase app initialized")
    return app
