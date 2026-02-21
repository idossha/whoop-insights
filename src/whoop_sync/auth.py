import json
import secrets
import urllib.parse
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import time
import requests

from .config import config


class CallbackHandler(BaseHTTPRequestHandler):
    auth_code = None
    error = None

    def do_GET(self):
        if self.path.startswith("/callback"):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

            if "code" in query:
                CallbackHandler.auth_code = query["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Success!</h1><p>You can close this window.</p>")
            elif "error" in query:
                CallbackHandler.error = query["error"][0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    f"<h1>Error</h1><p>{CallbackHandler.error}</p>".encode()
                )
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class WhoopAuth:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self._server = None

    def get_authorization_url(self, state: str = None) -> str:
        if state is None:
            state = secrets.token_urlsafe(16)

        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "scope": " ".join(config.scopes),
            "state": state,
        }

        return f"{config.auth_url}?{urllib.parse.urlencode(params)}"

    def start_callback_server(self, port: int = 8080) -> tuple:
        host = os.getenv("CALLBACK_HOST", "0.0.0.0")
        server = HTTPServer((host, port), CallbackHandler)
        thread = Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        self._server = server
        return server, thread

    def stop_callback_server(self):
        if self._server:
            self._server.shutdown()
            self._server = None

    def authorize(self, timeout: int = 300) -> bool:
        CallbackHandler.auth_code = None
        CallbackHandler.error = None

        server, thread = self.start_callback_server()

        auth_url = self.get_authorization_url()

        print("\n" + "=" * 70)
        print("AUTHENTICATION REQUIRED")
        print("=" * 70)
        print("\nVisit this URL in your browser to authenticate:")
        print(f"\n{auth_url}\n")
        print("=" * 70)
        print(f"\nWaiting for authorization (timeout: {timeout}s)...")

        start = time.time()
        while time.time() - start < timeout:
            if CallbackHandler.auth_code:
                self.stop_callback_server()
                print("Authorization code received!")
                return self.exchange_code_for_tokens(CallbackHandler.auth_code)
            if CallbackHandler.error:
                self.stop_callback_server()
                print(f"Authorization error: {CallbackHandler.error}")
                return False
            time.sleep(0.5)

        self.stop_callback_server()
        print("Authorization timed out")
        return False

    def exchange_code_for_tokens(self, code: str) -> bool:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }

        response = requests.post(config.token_url, data=data)

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data["refresh_token"]
            self.expires_at = time.time() + token_data.get("expires_in", 3600)
            self.save_tokens()
            print("Authentication successful! Tokens saved.")
            return True
        else:
            print(f"Token exchange failed: {response.text}")
            return False

    def refresh_access_token(self, max_retries: int = 3) -> bool:
        if not self.refresh_token:
            return False

        for attempt in range(max_retries):
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "scope": " ".join(config.scopes),
                "client_id": config.client_id,
                "client_secret": config.client_secret,
            }

            response = requests.post(config.token_url, data=data)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                self.refresh_token = token_data["refresh_token"]
                self.expires_at = time.time() + token_data.get("expires_in", 3600)
                self.save_tokens()
                return True
            elif response.status_code == 401 and attempt < max_retries - 1:
                print(
                    f"Token refresh failed (attempt {attempt + 1}/{max_retries}), retrying..."
                )
                time.sleep(2**attempt)
            else:
                print(f"Token refresh failed: {response.text}")
                return False

        return False

    def is_token_expired(self) -> bool:
        if not self.expires_at:
            return True
        return time.time() >= self.expires_at - 300

    def get_valid_access_token(self) -> str | None:
        if self.is_token_expired():
            if not self.refresh_access_token():
                return None
        return self.access_token

    def save_tokens(self):
        token_data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }
        with open(config.tokens_file, "w") as f:
            json.dump(token_data, f)

    def load_tokens(self) -> bool:
        try:
            with open(config.tokens_file, "r") as f:
                token_data = json.load(f)
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            self.expires_at = token_data.get("expires_at")
            return bool(self.access_token and self.refresh_token)
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    def is_authenticated(self) -> bool:
        return bool(self.access_token and self.refresh_token)

    def clear_tokens(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        if os.path.exists(config.tokens_file):
            os.remove(config.tokens_file)
