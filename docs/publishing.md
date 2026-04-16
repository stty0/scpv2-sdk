# PyPI 배포 가이드

## 업로드 순서

### 1. 빌드 도구 설치

```bash
pip install build twine
```

### 2. 패키지 빌드

```bash
python -m build
```

`dist/` 디렉토리에 `.tar.gz`(소스 배포)와 `.whl`(휠 배포) 파일이 생성됩니다.

### 3. TestPyPI에 먼저 테스트

```bash
twine upload --repository testpypi dist/*
```

설치 확인:

```bash
pip install --index-url https://test.pypi.org/simple/ scpv2-sdk
```

### 4. 실제 PyPI에 업로드

```bash
twine upload dist/*
```

---

## 설치 후 사용법

```bash
pip install scpv2-sdk
```

```python
import scpv2

# 명시적 자격증명
sess = scpv2.Session(
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY",
    region="kr-west1",
)

# 클라이언트 생성 및 API 호출
vpc = sess.client("vpc")
result = vpc.list_vpcs(size=20, page=0)
```

자격증명 자동 탐색 순서: 명시적 파라미터 → 환경변수(`SCP_ACCESS_KEY`, `SCP_SECRET_KEY`) → `~/.scp/credential.json`
