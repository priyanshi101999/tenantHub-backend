from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_host:str
    database_password:str
    database_port:int
    database_username:str
    database_name:str
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