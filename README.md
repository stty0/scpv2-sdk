# scpv2-sdk

Samsung SDS SCP (Samsung Cloud Platform) Python SDK.  
boto3와 동일한 개발자 경험을 제공합니다.

---

## Requirements

- Python 3.10 이상
- requests 2.28 이상

---

## Installation

```bash
pip install scpv2-sdk
```

---

## Credentials 설정

자격증명은 아래 순서로 자동 탐색합니다.

### 1. 명시적 파라미터

```python
import scpv2

sess = scpv2.Session(
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY",
)
```

### 2. 환경변수

```bash
export SCP_ACCESS_KEY="YOUR_ACCESS_KEY"
export SCP_SECRET_KEY="YOUR_SECRET_KEY"
export SCP_REGION="kr-west1"        # 선택
export SCP_ENVIRONMENT="e"          # 선택
```

```python
sess = scpv2.Session()  # 환경변수 자동 탐색
```

### 3. Credential 파일 (`~/.scp/credential.json`)

**단일 프로파일**

```json
{
    "access_key": "YOUR_ACCESS_KEY",
    "secret_key": "YOUR_SECRET_KEY",
    "region": "kr-west1",
    "environment": "e"
}
```

**다중 프로파일**

```json
{
    "default": {
        "access_key": "YOUR_ACCESS_KEY",
        "secret_key": "YOUR_SECRET_KEY",
        "region": "kr-west1"
    },
    "prod": {
        "access_key": "PROD_ACCESS_KEY",
        "secret_key": "PROD_SECRET_KEY",
        "region": "kr-east-1"
    }
}
```

```python
sess = scpv2.Session()                    # default 프로파일
sess = scpv2.Session(profile_name="prod") # prod 프로파일
```

---

## Basic Usage

### Session

```python
import scpv2

sess = scpv2.Session(
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY",
    region="kr-west1",      # 기본값: kr-west1
    environment="e",        # 기본값: e
    language="ko-KR",       # 기본값: ko-KR
)
```

### Client (저수준 API)

IDE 자동완성을 활용하려면 타입 힌트를 명시하는 것을 권장합니다.

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scpv2.stubs.vpc_client import VpcClient
    from scpv2.stubs.subnet_client import SubnetClient

# 타입 힌트를 지정하면 IDE에서 해당 서비스 메서드만 자동완성됩니다
vpc_client: VpcClient = sess.client("vpc")

# VPC 목록 조회
result = vpc_client.list_vpcs(size=20, page=0)
print(result["vpcs"])

# VPC 생성
vpc_client.create_vpc(
    name="my-vpc",
    cidr="10.0.0.0/24",
    description="My first VPC",
)

# VPC 삭제
vpc_client.delete_vpc(vpc_id="VPC_ID")

# 다른 서비스도 동일하게 타입 힌트 지정
subnet_client: SubnetClient = sess.client("subnet")
result = subnet_client.list_subnets(vpc_id="VPC_ID")
```

### Resource (고수준 OOP API)

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scpv2.stubs.vpc_resource import VpcResource

vpc: VpcResource = sess.resource("vpc")

# client 메서드를 의미있는 이름으로 접근
result = vpc.list()
vpc.create(name="my-vpc", cidr="10.0.0.0/24")
vpc.delete(vpc_id="VPC_ID")
```

---

## Paginator

대량의 결과를 페이지 단위로 자동 순회합니다.

```python
vpc_client = sess.client("vpc")
paginator = vpc_client.get_paginator("list_vpcs")

# 페이지 단위로 순회
for page in paginator.paginate(size=10):
    for vpc in page["vpcs"]:
        print(vpc["name"])

# 전체 결과를 한 번에 수집
result = paginator.paginate(size=10).build_full_result()
all_vpcs = result["vpcs"]
```

---

## Waiter

리소스가 특정 상태가 될 때까지 자동으로 폴링합니다.

```python
vpc_client = sess.client("vpc")

# VPC가 ACTIVE 상태가 될 때까지 대기 (5초 간격, 최대 20회)
waiter = vpc_client.get_waiter("vpc_active")
waiter.wait(id="VPC_ID")
print("VPC가 활성화됐습니다.")
```

---

## Collection

Resource에서 자동 페이지네이션을 지원하는 컬렉션 인터페이스입니다.

```python
vpc = sess.resource("vpc")

# 전체 순회
for v in vpc.vpcs.all():
    print(v["name"])

# 필터 적용
for v in vpc.vpcs.filter(state="ACTIVE"):
    print(v)

# 페이지 크기 지정
for v in vpc.vpcs.page_size(50):
    print(v)

# 처음 N개만
first_5 = vpc.vpcs.limit(5)
```

---

## Error Handling

```python
import scpv2

sess = scpv2.Session()
vpc_client = sess.client("vpc")

try:
    vpc_client.delete_vpc(vpc_id="INVALID_ID")

except scpv2.ClientError as e:
    # API가 에러 응답을 반환한 경우
    print(e.response["code"])       # 에러 코드
    print(e.response["message"])    # 에러 메시지
    print(e.operation_name)         # "delete_vpc"

except scpv2.ValidationError as e:
    # 파라미터 유효성 검사 실패 (API 호출 전 클라이언트 측)
    print(e)

except scpv2.CredentialError as e:
    # 자격증명을 찾을 수 없는 경우
    print(e)
```

---

## ResponseMetadata

모든 API 응답에 `ResponseMetadata`가 포함됩니다.

```python
result = vpc_client.list_vpcs()

meta = result["ResponseMetadata"]
print(meta["HTTPStatusCode"])   # 200
print(meta["RequestId"])        # 요청 ID
print(meta["RetryAttempts"])    # 실제 재시도 횟수
```

---

## Retry 설정

```python
from scpv2 import RetryConfig

sess = scpv2.Session(
    retry_config=RetryConfig(
        max_attempts=5,     # 최대 시도 횟수 (기본값: 3)
        mode="standard",    # "standard" (지수 백오프) | "legacy" (1초 고정)
    )
)
```

재시도 대상 HTTP 상태 코드: `429`, `500`, `502`, `503`, `504`

---

## Available Services

| service_name | 설명 |
|---|---|
| `"vpc"` | VPC 생성 / 조회 / 삭제 |
| `"subnet"` | 서브넷 생성 |
| `"virtualserver"` | 가상 서버 목록 / 상세 / 생성 / 시작 / 중지 |
| `"keypair"` | 키페어 목록 조회 / 생성 |

---

## Exception Hierarchy

```
ScpError
├── ClientError       # API 에러 응답 (4xx, 5xx)
├── ValidationError   # 파라미터 유효성 검사 실패
├── CredentialError   # 자격증명 없음 / 프로파일 없음
├── NoRegionError     # region 미설정
├── WaiterError       # Waiter 타임아웃 / 실패 상태 진입
└── PaginationError   # Paginator 설정 없음
```
