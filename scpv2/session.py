import os
import requests
from .credentials import CredentialResolver, ExplicitProvider, EnvProvider, FileProvider, SignatureGenerator


class Client:
    """저수준 API 베이스 클래스 (botocore.client.BaseClient와 동일)"""

    def __init__(self, session: "Session"):
        self._session = session

    def _get_headers(self, api_name: str, version: str, method: str = "GET", url: str = "") -> dict:
        """SCP API 요청 헤더 생성
        - Scp-Accesskey  : Access Key
        - Scp-Signature  : Base64(HMAC-SHA256(secret_key, method+url+timestamp+access_key+client_type))
        - Scp-Timestamp  : Unix timestamp (밀리초)
        - Scp-ClientType : 'Openapi'
        - Accept-Language: 언어 설정
        - Scp-Api-Version: '{api_name} {version}'
        """
        timestamp, signature = SignatureGenerator.generate(
            credentials=self._session.credentials,
            method=method,
            url=url,
        )
        return {
            "Scp-Accesskey":   self._session.credentials.access_key,
            "Scp-Signature":   signature,
            "Scp-Timestamp":   timestamp,
            "Scp-ClientType":  "Openapi",
            "Accept-Language": self._session.language,
            "Scp-Api-Version": f"{api_name} {version}",
        }

    def _request(
        self,
        http_method: str,
        path: str,
        api_name: str,
        version: str,
        query_params: dict = None,
        body: dict = None,
    ) -> dict:
        """SCP API에 실제 HTTP 요청을 보내고 JSON 응답을 반환"""
        url = f"{self._session.endpoint}{path}"
        # 서명에는 query string을 포함한 전체 URL 사용 (원본 SDK와 동일)
        if query_params:
            qs = "&".join(f"{k}={v}" for k, v in query_params.items() if v is not None)
            signed_url = f"{url}?{qs}" if qs else url
        else:
            signed_url = url
        headers = self._get_headers(api_name, version, method=http_method, url=signed_url)
        response = requests.request(
            method=http_method,
            url=url,
            headers=headers,
            params=query_params,
            json=body,
        )
        if not response.ok:
            print(f"[HTTP {response.status_code}] {response.text}")
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()

    @property
    def endpoint(self) -> str:
        """SCP 서비스 엔드포인트 URL"""
        return self._session.endpoint


class ServiceResource:
    """고수준 OOP API 베이스 클래스 (boto3.resources.base.ServiceResource와 동일)"""

    def __init__(self, client: Client):
        self._client = client


def _make_client(service_name: str, methods: dict) -> type:
    """클라이언트 클래스를 동적 생성 (boto3 ClientCreator와 동일)"""
    return type(service_name.upper(), (Client,), methods)


def _make_resource(service_name: str, methods: dict) -> type:
    """리소스 클래스를 동적 생성 (boto3 ResourceFactory와 동일)"""
    return type(f'{service_name.upper()}ServiceResource', (ServiceResource,), methods)


class Session:
    """SCP 연결 설정 관리 (boto3.Session과 동일)
    - 자격증명 체인: explicit → 환경변수 → ~/.scp/credential.json
    - 엔드포인트: https://vpc.{region}.{environment}.samsungsdscloud.com
    """

    _client_registry: dict = {}
    _resource_registry: dict = {}

    def __init__(
        self,
        access_key: str = None,
        secret_key: str = None,
        region: str = None,
        environment: str = None,
        language: str = None,
    ):
        # 자격증명 체인: explicit → env → ~/.scp/credential.json
        file_provider = FileProvider()
        resolver = CredentialResolver([
            ExplicitProvider(access_key, secret_key),
            EnvProvider(),
            file_provider,
        ])
        self.credentials = resolver.resolve()

        # region / environment / language: explicit → 환경변수 → credential.json → 기본값
        file_data = file_provider.data
        self.region = (
            region
            or os.environ.get("SCP_REGION")
            or file_data.get("region")
            or "kr-west1"
        )
        self.environment = (
            environment
            or os.environ.get("SCP_ENVIRONMENT")
            or file_data.get("environment")
            or "e"
        )
        self.language = (
            language
            or os.environ.get("SCP_LANGUAGE")
            or file_data.get("language")
            or "ko-KR"
        )
        self._clients: dict = {}
        self._resources: dict = {}

    @property
    def endpoint(self) -> str:
        """SCP API 엔드포인트 URL"""
        return f"https://vpc.{self.region}.{self.environment}.samsungsdscloud.com"

    @classmethod
    def register(cls, service_name: str, client_methods: dict, resource_methods: dict):
        """서비스 등록 — type()으로 클래스를 동적 생성하여 레지스트리에 등록"""
        cls._client_registry[service_name] = _make_client(service_name, client_methods)
        cls._resource_registry[service_name] = _make_resource(service_name, resource_methods)

    def client(self, service_name: str) -> Client:
        """저수준 Client 반환 — 서비스별 싱글톤"""
        if service_name not in self._clients:
            client_class = self._client_registry[service_name]
            self._clients[service_name] = client_class(session=self)
        return self._clients[service_name]

    def resource(self, service_name: str) -> ServiceResource:
        """고수준 ServiceResource 반환 — 서비스별 싱글톤"""
        if service_name not in self._resources:
            resource_class = self._resource_registry[service_name]
            self._resources[service_name] = resource_class(client=self.client(service_name))
        return self._resources[service_name]
