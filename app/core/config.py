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


    class Config:
        env_file=".env"


settings = Settings()