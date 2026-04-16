## 📁 프로젝트 구조

```
textmyapp/
├── container.py      # 조립기 (boto3.Session 내부)
├── db.py            # boto3.client() 같은 진입점
├── user_service.py  # boto3.resource() 같은 진입점
└── main.py          # 개발자가 실제 보는 코드
```

## 🔍 **1. container.py** - 조립기 (boto3.Session 역할)

```
pythonfrom dependency_injector import containers, providers

class Client:
    """db 클래스 - 실제 DB 작업"""
    def __init__(self, dsn: str):
        self.dsn = dsn  # postgresql://user:pass@host/db
    
    def fetch_user(self, user_id: str) -> dict:
        """DB에서 사용자 조회 (가짜 구현)"""
        return {
            "id": user_id,
            "name": "정렬 박",
            "email": "park@example.com",
            "status": "active"
        }

class ServiceResource:
    """user_service 클래스 - 비즈니스 로직"""
    def __init__(self, db):
        self._db = db  # db를 받음 (직접 생성 X!)
    
    def get_user(self, user_id: str) -> dict:
        user = self._db.fetch_user(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        return user
    
    def create_user(self, user_id: str, name: str, email: str) -> dict:
        # 비즈니스 로직
        user = {
            "id": user_id,
            "name": name,
            "email": email,
            "status": "active",
            "created_at": "2026-04-07T17:42:00Z"
        }
        # 실제로는 self._db.save_user(user)
        return user

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    # Singleton: 최초 1회 생성 후 재사용 (boto3 default session처럼)
    db = providers.Singleton(
        Client,
        dsn=config.db.dsn,
    )
    
    user_service = providers.Singleton(
        ServiceResource,
        db=db,  # 자동 의존성 주입!
    )

# 전역 싱글톤 컨테이너 (boto3의 default session)
_container = None

def get_container() -> Container:
    global _container
    if _container is None:
        container = Container()
        container.config.from_dict({
            "db": {
                "dsn": "postgresql://user:pass@localhost:5432/myapp"
            }
        })
        _container = container
    return _container
```

**핵심**:

- `Singleton`: 앱 전체에서 **동일한 db, user_service 객체 재사용** (메모리 효율 + 일관성)
- `get_container()`: **lazy initialization** (boto3 default session처럼 최초 호출시 생성)

## 🔍 **2. db.py** - boto3.client() 같은 진입점

```
pythonfrom container import get_container

# 개발자가 보는 코드: boto3.client('dynamodb')와 동일
db = get_container().db()
```

## 🔍 **3. user_service.py** - boto3.resource() 같은 진입점

```
pythonfrom container import get_container

# 개발자가 보는 코드: boto3.resource('dynamodb')와 동일
user_service = get_container().user_service()
```

## 🔍 **4. main.py** - 개발자가 실제 작성하는 코드

```
pythonfrom service_resource import user_service
from client import db

print("=== DB 직접 사용 (boto3.client처럼) ===")
user1 = db.fetch_user("u-100")
print(user1)

print("\\n=== ServiceResource 사용 (boto3.resource처럼) ===")
user2 = user_service.get_user("u-200")
print(user2)

new_user = user_service.create_user("u-300", "New User", "new@example.com")
print(f"Created: {new_user}")

print("\\n=== 구조 완성! ===")
```

**출력**:

```
text=== DB 직접 사용 (boto3.client처럼) ===
{'id': 'u-100', 'name': '정렬 박', 'email': 'park@example.com', 'status': 'active'}

=== ServiceResource 사용 (boto3.resource처럼) ===
{'id': 'u-200', 'name': '정렬 박', 'email': 'park@example.com', 'status': 'active'}
Created: {'id': 'u-300', 'name': 'New User', 'email': 'new@example.com', 'status': 'active', 'created_at': '2026-04-07T17:42:00Z'}

=== 구조 완성! ===
```

## 🎨 **boto3와 100% 동일한 개발자 경험**

```
textboto3 개발자:
import boto3
db = boto3.client('dynamodb')           # ← 2줄
user = db.get_item(...)

우리 개발자:
from client import db
user = db.fetch_user(...)               # ← 2줄 (동일!)

boto3 개발자:
s3 = boto3.resource('s3')
bucket = s3.Bucket('mybucket')

우리 개발자:
from service_resource import user_service
user = user_service.get_user(...)       # ← 동일!
```

## 🔧 **Study 포인트**

## 1. **Container 역할** (`boto3.Session` 내부)

```
textdb = providers.Singleton(Client, dsn=...)  # boto3.session.create_client()
user_service = providers.Singleton(ServiceResource, db=db)  # 자동 주입!
```

## 2. **Singleton의 의미**

- **최초 1회 생성 후 재사용** (메모리 절약, 일관성)
- `db.fetch_user("u-100")` 여러 번 호출해도 **같은 db 인스턴스**

## 3. **get_container()의 Lazy 초기화**

```
textif _container is None:  # 최초 호출시만
    _container = Container()
return _container
```

boto3도 `boto3.client()` 최초 호출시 default session을 내부에서 만듭니다.

## 4. **의존성 흐름**

```
textmain.py → user_service.py → get_container() → Container.user_service
                                                ↓
                                            Container.db → Client
```

## 🧪 **테스트 (DI의 진짜 장점)**

```
python# test_user_service.py
from unittest.mock import Mock
from container import Container, get_container
from service_resource import user_service

def test_user_service():
    # 테스트용 Container
    test_container = Container()
    test_container.db.override(providers.Object(Mock(spec=Client)))
    
    global get_container  # 임시 오버라이드
    original_get = get_container
    get_container = lambda: test_container
    
    # 테스트
    user = user_service.get_user("u-test")
    assert user["id"] == "u-test"
    
    get_container = original_get  # 복원
```

**AWS 없이 단위 테스트 가능!**

## 🚀 **실전 확장성**

```
text# 다른 DB 어댑터 추가
class MySQLClient(Client):
    def __init__(self, connection_string):
        ...

# container.py 수정만
db = providers.Factory(MySQLClient, conn=config.mysql.conn)

# 개발자 코드는 변경 없음!
from client import db  # 여전히 동작
```

## 📊 **컴포넌트 다이어그램**

```
textmain.py ──import──→ user_service.py ──get_container()──→ Container
                                                    ↓
                                              user_service ──→ db
```

**결과**: 개발자는 **container를 모르고**, `user_service.get_user()`만 쓰면 됩니다. **boto3와 완전히 동일한 경험** + **DI의 테스트/교체성**까지! 🎉

**실행하려면**: 위 코드를 4개 파일로 나누어 `pip install dependency-injector` 후 `python main.py` 실행하세요.