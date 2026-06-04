from firebase_admin import initialize_app
from firebase_admin import credentials

cred = credentials.Certificate("firebase_service_account.json")
initialize_app(cred)