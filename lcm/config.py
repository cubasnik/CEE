import os


class Settings:
    def __init__(self) -> None:
        origins = os.getenv("CORS_ORIGINS", "*")
        self.CORS_ORIGINS = [item.strip() for item in origins.split(",") if item.strip()]


settings = Settings()
