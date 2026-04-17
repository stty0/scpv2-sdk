"""
scpv2.session — Session / Client / ServiceResource (boto3.session과 동일한 구조)

boto3 대응:
    Session         ←→ boto3.Session
    Client          ←→ botocore.client.BaseClient
    ServiceResource ←→ boto3.resources.base.ServiceResource
"""
import os
import requests as _requests

from .credentials import (
    CredentialResolver, ExplicitProvider, EnvProvider,
    FileProvider, SignatureGenerator,
)
from .exceptions  import ClientError, PaginationError, WaiterError
from .paginator   import Paginator
from .response    import build_response
from .retries     import RetryConfig, RetryHandler
from .waiter      import Waiter


# ── 저수준 Client ────────────────────────────────────────────────────────────

class Client:
    """저수준 API 베이스 클래스 (botocore.client.BaseClient와 동일)

    서브클래스는 Session.register()가 type()으로 동적 생성합니다.
    직접 인스턴스화하지 않고 session.client("서비스명")으로 획득합니다.
    """

    def __init__(self, session: "Session"):
        self._session = session
        self._retry   = RetryHandler(session.retry_config)

    # ── 헤더 / HTTP ──────────────────────────────────────────────────────

    def _get_headers(
        self,
        api_name: str,
        version: str,
        method: str = "GET",
        url: str = "",
    ) -> dict:
        """SCP API 요청 헤더 생성 (서명 포함)"""
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
        operation_name: str = "Unknown",
    ) -> dict:
        """SCP API HTTP 요청 — retry + ResponseMetadata 포함

        Args:
            http_method:     HTTP 동사 (GET, POST, DELETE, PUT, PATCH)
            path:            API 경로 (/v1/vpcs 등)
            api_name:        Scp-Api-Version 헤더용 서비스명
            version:         Scp-Api-Version 헤더용 버전
            query_params:    쿼리 파라미터 dict
            body:            요청 바디 dict (JSON)
            operation_name:  ClientError 메시지에 포함할 메서드 이름

        Returns:
            응답 dict (ResponseMetadata 포함)

        Raises:
            ClientError: API가 에러 응답을 반환하거나 재시도 횟수를 초과한 경우
        """
        url = f"{self._session.endpoint}{path}"

        # 서명에는 query string을 포함한 전체 URL 사용
        if query_params:
            qs = "&".join(
                f"{k}={v}" for k, v in query_params.items() if v is not None
            )
            signed_url = f"{url}?{qs}" if qs else url
        else:
            signed_url = url

        last_exc = None
        for attempt in range(self._retry.config.max_attempts):
            headers = self._get_headers(api_name, version, method=http_method, url=signed_url)
            http_resp = _requests.request(
                method=http_method,
                url=url,
                headers=headers,
                params=query_params,
                json=body,
            )

            if http_resp.ok:
                data = http_resp.json() if http_resp.content else {}
                return build_response(data, http_resp, retry_attempts=attempt)

            # 재시도 가능한 에러
            if (
                self._retry.is_retryable(http_resp.status_code)
                and attempt < self._retry.config.max_attempts - 1
            ):
                self._retry.backoff(attempt)
                continue

            # 재시도 불가 에러 → ClientError
            try:
                error_data = http_resp.json()
            except Exception:
                error_data = {}
            # HTTP 상태코드와 raw body는 항상 포함 (필드명이 달라도 디버깅 가능)
            error_data.setdefault("_status", http_resp.status_code)
            error_data.setdefault("_body",   http_resp.text)
            raise ClientError(error_data, operation_name)

        raise ClientError(
            {"code": "MaxRetriesExceeded", "message": "Max retry attempts exceeded"},
            operation_name,
        )

    # ── Paginator / Waiter ────────────────────────────────────────────────

    def get_paginator(self, operation_name: str) -> Paginator:
        """페이지네이터를 반환합니다 (boto3 client.get_paginator와 동일)

        Args:
            operation_name: 페이지네이션할 Client 메서드 이름 (예: "list_vpcs")

        Returns:
            Paginator 객체

        Raises:
            PaginationError: 해당 operation에 paginator 설정이 없는 경우
        """
        service_name = self._service_name
        configs = Session._paginator_config_registry.get(service_name, {})
        if operation_name not in configs:
            raise PaginationError(
                f"No paginator found for operation '{operation_name}' "
                f"on service '{service_name}'"
            )
        method = getattr(self, operation_name)
        return Paginator(method, configs[operation_name])

    def get_waiter(self, waiter_name: str) -> Waiter:
        """웨이터를 반환합니다 (boto3 client.get_waiter와 동일)

        Args:
            waiter_name: 웨이터 이름 (예: "vpc_active")

        Returns:
            Waiter 객체

        Raises:
            WaiterError: 해당 이름의 waiter 설정이 없는 경우
        """
        service_name = self._service_name
        configs = Session._waiter_config_registry.get(service_name, {})
        if waiter_name not in configs:
            raise WaiterError(
                waiter_name,
                f"No waiter configuration found for '{waiter_name}' "
                f"on service '{service_name}'"
            )
        return Waiter(waiter_name, configs[waiter_name], self)

    @property
    def endpoint(self) -> str:
        return self._session.endpoint


# ── 고수준 ServiceResource ───────────────────────────────────────────────────

class ServiceResource:
    """고수준 OOP API 베이스 클래스 (boto3.resources.base.ServiceResource와 동일)

    서브클래스는 Session.register()가 type()으로 동적 생성합니다.
    CollectionManager 디스크립터가 주입되어 .vpcs, .virtual_servers 등 컬렉션 속성을 제공합니다.
    """

    def __init__(self, client: Client):
        self._client = client


# ── 동적 클래스 팩토리 ────────────────────────────────────────────────────────

def _make_client(service_name: str, methods: dict) -> type:
    """Client 서브클래스를 동적 생성 (boto3 ClientCreator와 동일)"""
    attrs = {"_service_name": service_name, **methods}
    return type(service_name.upper(), (Client,), attrs)


def _make_resource(service_name: str, methods: dict, collection_managers: dict = None) -> type:
    """ServiceResource 서브클래스를 동적 생성 (boto3 ResourceFactory와 동일)

    CollectionManager 디스크립터를 attrs에 포함시키면 __set_name__이 자동 호출됩니다.
    """
    attrs = {**methods, **(collection_managers or {})}
    return type(f"{service_name.upper()}ServiceResource", (ServiceResource,), attrs)


# ── Session ──────────────────────────────────────────────────────────────────

class Session:
    """SCP 연결 및 서비스 클라이언트 관리 (boto3.Session과 동일)

    자격증명 탐색 순서:
        1. 생성자 파라미터 (access_key, secret_key)
        2. 환경변수 SCP_ACCESS_KEY / SCP_SECRET_KEY
        3. ~/.scp/credential.json (profile_name 지정 가능)

    사용 예::

        # 자동 탐색
        sess = scpv2.Session()

        # 명시적 자격증명
        sess = scpv2.Session(access_key="...", secret_key="...", region="kr-west1")

        # 프로파일 지정
        sess = scpv2.Session(profile_name="prod")
    """

    # 서비스 레지스트리 (모든 Session 인스턴스가 공유)
    _client_registry:            dict = {}
    _resource_registry:          dict = {}
    _paginator_config_registry:  dict = {}
    _waiter_config_registry:     dict = {}

    def __init__(
        self,
        access_key:   str = None,
        secret_key:   str = None,
        region:       str = None,
        environment:  str = None,
        language:     str = None,
        profile_name: str = "default",
        retry_config: RetryConfig = None,
    ):
        file_provider = FileProvider(profile_name=profile_name)
        resolver = CredentialResolver([
            ExplicitProvider(access_key, secret_key),
            EnvProvider(),
            file_provider,
        ])
        self.credentials  = resolver.resolve()
        self.retry_config = retry_config or RetryConfig()

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

        self._clients:   dict = {}
        self._resources: dict = {}

    @property
    def endpoint(self) -> str:
        return f"https://vpc.{self.region}.{self.environment}.samsungsdscloud.com"

    # ── 서비스 등록 (ServiceLoader가 호출) ──────────────────────────────

    @classmethod
    def register(
        cls,
        service_name:       str,
        client_methods:     dict,
        resource_methods:   dict,
        collection_managers: dict = None,
        paginator_configs:  dict = None,
        waiter_configs:     dict = None,
    ):
        """JSON 정의로부터 서비스를 레지스트리에 등록"""
        cls._client_registry[service_name]   = _make_client(service_name, client_methods)
        cls._resource_registry[service_name] = _make_resource(
            service_name, resource_methods, collection_managers
        )
        if paginator_configs:
            cls._paginator_config_registry[service_name] = paginator_configs
        if waiter_configs:
            cls._waiter_config_registry[service_name] = waiter_configs

    # ── 클라이언트 / 리소스 반환 ─────────────────────────────────────────

    def client(self, service_name: str) -> Client:
        """저수준 Client 반환 — 서비스별 싱글톤 (boto3 session.client와 동일)"""
        if service_name not in self._clients:
            client_class = self._client_registry[service_name]
            self._clients[service_name] = client_class(session=self)
        return self._clients[service_name]

    def resource(self, service_name: str) -> ServiceResource:
        """고수준 ServiceResource 반환 — 서비스별 싱글톤 (boto3 session.resource와 동일)"""
        if service_name not in self._resources:
            resource_class = self._resource_registry[service_name]
            self._resources[service_name] = resource_class(client=self.client(service_name))
        return self._resources[service_name]
