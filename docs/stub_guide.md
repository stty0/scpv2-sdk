# Stub 파일 자동 생성 가이드

## 개요

`generate_stubs.py`는 `resources/data/*.json` 서비스 정의를 읽어서 IDE 자동완성용 `.pyi` stub 파일을 자동 생성합니다.  
boto3의 `mypy_boto3_builder`와 동일한 방식입니다.

---

## 생성 파일

| 파일 | 설명 |
|------|------|
| `{service}_client.pyi` | 서비스별 Client 클래스 타입 정의 |
| `session.pyi` | `Session.client()` overload 타입 정의 |

---

## 사용법

### 1. stub 파일 생성

```bash
python generate_stubs.py
```

실행 결과:
```
생성: ec2_client.pyi
생성: vpc_client.pyi
생성: session.pyi

총 2개 서비스 stub 생성 완료: ec2, vpc
```

### 2. 자동완성 확인

stub 파일 생성 후 VS Code에서 아래와 같이 자동완성이 동작합니다.

```python
sess = Session()
vpc_client = sess.client("vpc")  # → VpcClient 타입으로 인식
vpc_client.create_vpc(           # → 파라미터 자동완성
    name=...,
    cidr=...,
)
```

---

## 새 서비스 추가 시 워크플로우

```
1. resources/data/{service}.json 작성
         ↓
2. python generate_stubs.py 실행
         ↓
3. {service}_client.pyi + session.pyi 자동 갱신
         ↓
4. IDE 자동완성 즉시 반영
```

---

## 파라미터 타입 추론 규칙

| 파라미터 이름 | 추론 타입 |
|--------------|-----------|
| `size`, `page`, `count` | `int` |
| `tags` | `list` |
| 그 외 | `str` |

`required` 목록에 있으면 필수(`str`), 없으면 optional(`str \| None = None`)로 생성됩니다.

### 예시 — `vpc.json`의 `create_vpc`

```json
{
    "params": ["name", "cidr", "description", "tags"],
    "required": ["name", "cidr"]
}
```

생성되는 stub:

```python
def create_vpc(
    self,
    name: str,           # required
    cidr: str,           # required
    description: str | None = None,   # optional
    tags: list | None = None,         # optional
) -> dict: ...
```

---

## 주의사항

- stub 파일은 **자동 생성 파일**입니다. 직접 수정하지 마세요.
- JSON을 변경하면 반드시 `python generate_stubs.py`를 다시 실행하세요.
- stub 파일은 타입 힌트 전용이며 실제 실행에는 영향을 주지 않습니다.
