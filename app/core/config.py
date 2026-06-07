from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_host:str
    postgres_password:str
    postgres_port:int
    postgres_user:str
    postgres_db:str
    database_url:str
    sendgrid_api_key:str
    sender_mail:str
    otp_expire_minutes:int
    access_token_expire_minutes:int
    refresh_token_expire_days:int
    algorithm:str
    secret_key:str
    redis_host:str
    redis_port:int
    frontend_baseurl:str
    stripe_secret_key:str
    stripe_webhook_secret:str
    twilio_account_sid:str
    twilio_auth_token:str
    twilio_service_sid:str
    redis_url:str
    
    class Config:
        env_file=".env"


settings = Settings()