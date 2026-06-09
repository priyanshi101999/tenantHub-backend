from firebase_admin import get_app, initialize_app
from firebase_admin import credentials

try:
    get_app()
except ValueError:
    cred = credentials.Certificate("firebase_service_account.json")
    initialize_app(cred)
