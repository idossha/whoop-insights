import os
from typing import List, Optional
from dotenv import load_dotenv
from dataclasses import dataclass, field

load_dotenv()


@dataclass
class Config:
    client_id: str = os.getenv("WHOOP_CLIENT_ID", "")
    client_secret: str = os.getenv("WHOOP_CLIENT_SECRET", "")
    redirect_uri: str = os.getenv(
        "WHOOP_REDIRECT_URI", "http://localhost:8080/callback"
    )
    db_path: str = os.getenv("WHOOP_DB_PATH", "whoop.db")
    tokens_file: str = os.getenv("WHOOP_TOKENS_FILE", "tokens.json")

    auth_url: str = "https://api.prod.whoop.com/oauth/oauth2/auth"
    token_url: str = "https://api.prod.whoop.com/oauth/oauth2/token"
    api_base_url: str = "https://api.prod.whoop.com"

    scopes: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.scopes:
            self.scopes = [
                "offline",
                "read:recovery",
                "read:cycles",
                "read:workout",
                "read:sleep",
                "read:profile",
                "read:body_measurement",
            ]

    def validate(self) -> bool:
        if not self.client_id or not self.client_secret:
            return False
        return True


config = Config()
