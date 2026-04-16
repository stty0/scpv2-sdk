import base64
import hashlib
import hmac
import json
import os
import time


class Credentials:
    """SCP 자격증명 보관 (access_key, secret_key)"""
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key


class SignatureGenerator:
    """SCP API 요청 서명 생성
    - message = method + url + timestamp + access_key + client_type
    - Scp-Signature = Base64(HMAC-SHA256(secret_key, message))
    - Scp-Timestamp = Unix timestamp (밀리초)
    """

    @staticmethod
    def generate(
        credentials: Credentials,
        method: str,
        url: str,
        client_type: str = "Openapi",
    ) -> tuple[str, str]:
        """(timestamp, signature) 반환"""
        timestamp = str(int(time.time() * 1000))
        message = method.upper() + url + timestamp + credentials.access_key + client_type
        signature = base64.b64encode(
            hmac.new(
                credentials.secret_key.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")
        return timestamp, signature


# ── Credential Providers ────────────────────────────────────────────────────

class ExplicitProvider:
    """1순위: 코드에서 명시적으로 전달한 파라미터"""
    METHOD = "explicit"

    def __init__(self, access_key: str = None, secret_key: str = None):
        self._access_key = access_key
        self._secret_key = secret_key

    def load(self) -> Credentials | None:
        if self._access_key and self._secret_key:
            return Credentials(self._access_key, self._secret_key)
        return None


class EnvProvider:
    """2순위: 환경변수 (SCP_ACCESS_KEY, SCP_SECRET_KEY)"""
    METHOD = "env"
    ENV_ACCESS_KEY = "SCP_ACCESS_KEY"
    ENV_SECRET_KEY = "SCP_SECRET_KEY"

    def load(self) -> Credentials | None:
        access_key = os.environ.get(self.ENV_ACCESS_KEY)
        secret_key = os.environ.get(self.ENV_SECRET_KEY)
        if access_key and secret_key:
            return Credentials(access_key, secret_key)
        return None


class FileProvider:
    """3순위: ~/.scp/credential.json 파일"""
    METHOD = "file"
    CREDENTIAL_FILE = os.path.join(os.path.expanduser("~"), ".scp", "credential.json")

    def __init__(self):
        self._data: dict = {}

    def load(self) -> Credentials | None:
        if not os.path.exists(self.CREDENTIAL_FILE):
            return None
        with open(self.CREDENTIAL_FILE) as f:
            self._data = json.load(f)
        access_key = self._data.get("access_key")
        secret_key = self._data.get("secret_key")
        if not access_key or not secret_key:
            return None
        return Credentials(access_key, secret_key)

    @property
    def data(self) -> dict:
        return self._data


# ── Credential Resolver ─────────────────────────────────────────────────────

class CredentialResolver:
    """자격증명 체인 리졸버 — providers 순서대로 시도"""

    def __init__(self, providers: list):
        self.providers = providers

    def resolve(self) -> Credentials:
        for provider in self.providers:
            credentials = provider.load()
            if credentials:
                return credentials
        raise RuntimeError(
            "SCP 자격증명을 찾을 수 없습니다. 다음 중 하나를 설정하세요:\n"
            "  1. Session(access_key=..., secret_key=...)\n"
            f"  2. 환경변수: {EnvProvider.ENV_ACCESS_KEY}, {EnvProvider.ENV_SECRET_KEY}\n"
            f"  3. 파일: {FileProvider.CREDENTIAL_FILE}"
        )
