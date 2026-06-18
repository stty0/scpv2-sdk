"""
scpv2.credentials — 자격증명 관리

자격증명 탐색 순서:
    1. ExplicitProvider  — Session(access_key=..., secret_key=...)
    2. EnvProvider       — 환경변수 SCP_ACCESS_KEY / SCP_SECRET_KEY
    3. FileProvider      — ~/.scp/credential.json

다중 프로파일 (~/.scp/credential.json)::

    # 단일 프로파일 (기존 형식, 하위 호환)
    {
        "access_key": "...",
        "secret_key": "...",
        "region":     "kr-west1"
    }

    # 다중 프로파일
    {
        "default": {
            "access_key": "...",
            "secret_key": "...",
            "region":     "kr-west1"
        },
        "prod": {
            "access_key": "...",
            "secret_key": "...",
            "region":     "kr-east-1"
        }
    }

사용 예::

    # default 프로파일 사용
    sess = scpv2.Session()

    # 명시적 프로파일 지정
    sess = scpv2.Session(profile_name="prod")
"""
import base64
import hashlib
import hmac
import json
import os
import time

from .exceptions import CredentialError


class Credentials:
    """SCP 자격증명 보관 (access_key, secret_key)"""
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key


class SignatureGenerator:
    """SCP API 요청 서명 생성

    서명 메시지: method + url + timestamp + access_key + client_type
    알고리즘:    Base64(HMAC-SHA256(secret_key, message))
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
        message   = method.upper() + url + timestamp + credentials.access_key + client_type
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
    """1순위: Session() 생성자에 직접 전달한 파라미터"""
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
    """3순위: ~/.scp/credential.json 파일

    단일 프로파일(기존 형식)과 다중 프로파일 형식을 모두 지원합니다.
    profile_name을 지정하지 않으면 "default" 프로파일 또는 루트 레벨 키를 사용합니다.
    """
    METHOD = "file"
    CREDENTIAL_FILE = os.path.join(os.path.expanduser("~"), ".scp", "credential.json")

    def __init__(self, profile_name: str = "default"):
        self._profile_name = profile_name
        self._data: dict = {}

    def load(self) -> Credentials | None:
        if not os.path.exists(self.CREDENTIAL_FILE):
            return None
        with open(self.CREDENTIAL_FILE, encoding="utf-8") as f:
            raw = json.load(f)

        # 다중 프로파일 형식 감지: 최상위에 access_key가 없으면 프로파일 형식
        if "access_key" not in raw:
            profile = raw.get(self._profile_name) or raw.get("default")
            if not profile:
                available = list(raw.keys())
                raise CredentialError(
                    f"Profile '{self._profile_name}' not found in {self.CREDENTIAL_FILE}. "
                    f"Available profiles: {available}"
                )
            self._data = profile
        else:
            # 기존 단일 프로파일 형식 (하위 호환)
            self._data = raw

        access_key = self._data.get("access_key")
        secret_key = self._data.get("secret_key")
        if not access_key or not secret_key:
            return None
        return Credentials(access_key, secret_key)

    @property
    def data(self) -> dict:
        """로드된 프로파일 데이터 (region, environment, language 등 포함)"""
        return self._data


# ── Credential Resolver ─────────────────────────────────────────────────────

class CredentialResolver:
    """자격증명 체인 리졸버 — providers를 순서대로 시도해 처음 찾은 자격증명을 반환"""

    def __init__(self, providers: list):
        self.providers = providers

    def resolve(self) -> Credentials:
        for provider in self.providers:
            credentials = provider.load()
            if credentials:
                return credentials
        raise CredentialError(
            "SCP 자격증명을 찾을 수 없습니다. 다음 중 하나를 설정하세요:\n"
            "  1. Session(access_key=..., secret_key=...)\n"
            f"  2. 환경변수: {EnvProvider.ENV_ACCESS_KEY}, {EnvProvider.ENV_SECRET_KEY}\n"
            f"  3. 파일: {FileProvider.CREDENTIAL_FILE}"
        )
