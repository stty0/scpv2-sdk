# Component Diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#e8f4fb', 'primaryBorderColor': '#7eb8d4', 'primaryTextColor': '#333', 'lineColor': '#999'}}}%%
classDiagram

    %% ── 스타일 정의 ──
    classDef ivory   fill:#fdfcee,stroke:#c8b89a,color:#333
    classDef sky     fill:#e8f4fb,stroke:#7eb8d4,color:#333
    classDef mint    fill:#eaf7f0,stroke:#7ec4a0,color:#333
    classDef orange  fill:#fef3e8,stroke:#d4a06a,color:#333
    classDef dynamic fill:#eef3fb,stroke:#a0b4d4,color:#555,stroke-dasharray:4 4

    %% ── credentials.py ──
    class Credentials {
        +access_key: str
        +secret_key: str
        +token: str
    }

    class ExplicitProvider {
        METHOD = "explicit"
        +load() Credentials
    }

    class EnvProvider {
        METHOD = "env"
        ENV_ACCESS_KEY = "SCP_ACCESS_KEY"
        ENV_SECRET_KEY = "SCP_SECRET_KEY"
        +load() Credentials
    }

    class FileProvider {
        METHOD = "file"
        CREDENTIAL_FILE = "~/.scp/credential.json"
        +load() Credentials
        +data() dict
    }

    class CredentialResolver {
        +providers: list
        +resolve() Credentials
    }

    %% ── session.py ──
    class Client {
        -_session: Session
    }

    class ServiceResource {
        -_client: Client
    }

    class Session {
        +credentials: Credentials
        +region: str
        +dsn: str
        -_client_registry: dict
        -_resource_registry: dict
        -_clients: dict
        -_resources: dict
        +register(service_name, client_methods, resource_methods)
        +client(service_name) Client
        +resource(service_name) ServiceResource
    }

    class _make_client {
        <<factory>>
        type(name, Client, methods)
    }

    class _make_resource {
        <<factory>>
        type(name, ServiceResource, methods)
    }

    %% ── 동적 생성 클래스 (런타임) ──
    class EC2 {
        <<dynamic>>
        +describe_instances(instance_id) dict
        +start_instances(instance_id) dict
        +stop_instances(instance_id) dict
    }

    class S3 {
        <<dynamic>>
        +get_object(bucket, key) dict
        +put_object(bucket, key, body) dict
        +list_objects_v2(bucket) dict
    }

    class EC2ServiceResource {
        <<dynamic>>
        +Instance(instance_id) dict
        +start(instance_id) dict
        +stop(instance_id) dict
    }

    class S3ServiceResource {
        <<dynamic>>
        +Bucket(bucket_name) dict
        +Object(bucket, key) dict
        +upload(bucket, key, body) dict
    }

    %% ── 스타일 적용 ──
    class Credentials:::ivory
    class ExplicitProvider:::orange
    class EnvProvider:::orange
    class FileProvider:::orange
    class CredentialResolver:::orange
    class Session:::ivory
    class Client:::sky
    class ServiceResource:::sky
    class _make_client:::mint
    class _make_resource:::mint
    class EC2:::dynamic
    class S3:::dynamic
    class EC2ServiceResource:::dynamic
    class S3ServiceResource:::dynamic

    %% ── 관계: 자격증명 체인 ──
    CredentialResolver o-- ExplicitProvider  : 1순위
    CredentialResolver o-- EnvProvider       : 2순위
    CredentialResolver o-- FileProvider      : 3순위
    CredentialResolver ..> Credentials       : resolve()

    Session ..> CredentialResolver           : uses at __init__
    Session "1" *-- "1" Credentials          : has

    %% ── 관계: 서비스 팩토리 ──
    Session ..> _make_client                 : calls at register()
    Session ..> _make_resource               : calls at register()

    _make_client  ..> EC2                    : type() 동적 생성
    _make_client  ..> S3                     : type() 동적 생성
    _make_resource ..> EC2ServiceResource    : type() 동적 생성
    _make_resource ..> S3ServiceResource     : type() 동적 생성

    EC2              --|> Client              : extends (동적)
    S3               --|> Client              : extends (동적)
    EC2ServiceResource --|> ServiceResource   : extends (동적)
    S3ServiceResource  --|> ServiceResource   : extends (동적)

    EC2ServiceResource "n" --o "1" EC2       : uses
    S3ServiceResource  "n" --o "1" S3        : uses
    Client "n" --o "1" Session               : uses
```

## 파일 구조

```
credentials.py      Credentials
                    ExplicitProvider, EnvProvider, FileProvider
                    CredentialResolver
session.py          Client (base), ServiceResource (base)
                    _make_client(), _make_resource()  ← 클래스 동적 생성 팩토리
                    Session                           ← 레지스트리 + 접근 진입점
resources/
    __init__.py     리소스 일괄 등록
    loader.py       ServiceLoader — JSON → 메서드 동적 생성
    data/
        ec2.json    EC2 서비스 정의
        s3.json     S3 서비스 정의
container.py        get_session() — 전역 Session 싱글톤
client.py           get_session().client('ec2')
service_resource.py get_session().resource('s3')
~/.scp/
    credential.json 자격증명 파일 (access_key, secret_key, region, dsn)
main.py             진입점
```

## boto3와의 대응

| boto3 내부 | 이 프로젝트 | 역할 |
|---|---|---|
| `botocore.credentials.Credentials` | `Credentials` | 자격증명 보관 |
| `botocore.credentials.EnvProvider` | `EnvProvider` | 환경변수에서 자격증명 로드 |
| `botocore.credentials.SharedCredentialProvider` | `FileProvider` | 파일에서 자격증명 로드 |
| `botocore.credentials.CredentialResolver` | `CredentialResolver` | 자격증명 체인 관리 |
| `botocore.client.BaseClient` | `Client` | 저수준 API 베이스 |
| `boto3.resources.base.ServiceResource` | `ServiceResource` | 고수준 API 베이스 |
| `ClientCreator.create_client()` | `_make_client()` | `type()`으로 클래스 동적 생성 |
| `ResourceFactory.load_from_definition()` | `_make_resource()` | `type()`으로 클래스 동적 생성 |
| `botocore/data/{service}/service-2.json` | `resources/data/ec2.json` | 서비스 정의 |
| `~/.aws/credentials` + `~/.aws/config` | `~/.scp/credential.json` | 자격증명 + 설정 파일 |
| `boto3.Session` | `Session` | 레지스트리 + 싱글톤 관리 |

## 자격증명 체인 흐름

```
Session() 생성
    → CredentialResolver.resolve()
        → ExplicitProvider.load()   # Session(access_key=...) 로 명시한 경우
              ↓ None이면
        → EnvProvider.load()        # SCP_ACCESS_KEY, SCP_SECRET_KEY 환경변수
              ↓ None이면
        → FileProvider.load()       # ~/.scp/credential.json
              ↓ None이면
        → RuntimeError("자격증명을 찾을 수 없습니다")
```

## 서비스 등록 흐름

```
resources/__init__.py → ServiceLoader.load_all()
    → resources/data/ec2.json 읽기
        → _make_client_method() 로 Client 메서드 동적 생성
        → _make_resource_method() 로 ServiceResource 메서드 동적 생성
        → Session.register('ec2', client_methods, resource_methods)
            → _make_client('ec2', {...}) → type('EC2', (Client,), {...})
            → _make_resource('ec2', {...}) → type('EC2ServiceResource', ...)
            → 레지스트리에 저장

sess.client('ec2') 호출
    → 레지스트리에서 EC2 클래스 조회
    → EC2(session=self) 인스턴스 생성 및 캐시 → 반환
```
