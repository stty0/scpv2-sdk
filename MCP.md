scpv2-sdk × fastmcp 기반 MCP 서버 설계안
1. 핵심 통찰 — SDK의 강점을 그대로 활용한다
SDK 구조를 분석한 결과, MCP 서버 설계의 출발점은 명확합니다:

SDK 특성	MCP 설계에 미치는 영향
scpv2/resources/data/*.json에 서비스 정의가 선언적으로 들어있음	JSON → MCP tool 자동 등록이 가능 → 손으로 안 적어도 됨
Session._client_registry가 런타임에 모든 서비스/메서드 보유	리플렉션으로 메서드 시그니처/파라미터/검증 룰을 그대로 가져올 수 있음
ValidationError / ClientError로 에러가 표준화됨	MCP 에러 매핑이 단순함
ResponseMetadata가 모든 응답에 포함 → 크기가 큼	LLM에게는 노이즈 → 응답 슬리밍(shaping) 필요
Paginator/Waiter가 boto3 스타일로 분리됨	MCP에선 페이지네이션을 숨기거나 평탄화해야 LLM이 다루기 쉬움
자격증명이 chain resolver (Explicit→Env→File)	MCP 서버는 그대로 위임 — 별도 처리 불필요
➡ 결론: 새 어댑터 계층(scpv2_mcp/)을 하나 만들어 JSON 정의를 fastmcp @tool로 자동 변환하는 메타프로그래밍 접근이 가장 깔끔합니다.

2. 패키지 구조

scpv2-sdk/
├── scpv2/                       # 기존 SDK (수정 없음)
├── scpv2_mcp/                   # ★ 신규 MCP 어댑터
│   ├── __init__.py
│   ├── server.py                # fastmcp 인스턴스 + 엔트리포인트
│   ├── factory.py               # JSON → fastmcp.tool 변환기
│   ├── shaping.py               # 응답 슬리밍/요약
│   ├── errors.py                # SDK 예외 → MCP 에러 dict
│   ├── annotations.py           # destructive/readOnly 메타데이터
│   ├── descriptions.py          # LLM-친화 설명 오버라이드
│   ├── config.py                # pydantic-settings 설정
│   └── policies.py              # read-only / profile allowlist
├── scpv2_mcp_overrides/         # ★ 운영자가 손수 다듬을 영역
│   └── tools.yaml               # 도구별 설명/예시/별칭
├── main_mcp.py                  # 개발용 진입점
└── pyproject.toml               # [project.optional-dependencies] mcp = ["fastmcp"]
기존 SDK 패키지는 건드리지 않습니다 (단일 책임 유지, SDK 단독 배포 가능).

3. 인증/세션 전략

┌─────────────────────────────────────────────────┐
│ MCP 서버 부팅                                    │
│  1. config.py → SCP_PROFILE, SCP_REGION 등 로드  │
│  2. profile_allowlist 검증                       │
│  3. Session 풀 생성 (profile별 lazy 초기화)      │
└─────────────────────────────────────────────────┘
                  ↓
   tool 호출 시 → SessionPool.get(profile) → Client
단일 프로파일 모드 (기본): SCP_PROFILE=default
다중 프로파일 모드: tool에 profile 파라미터를 옵션으로 노출
자격증명 자체는 MCP 서버 응답에 절대 포함하지 않음 (로그 마스킹 포함)
4. 도구(Tool) 생성 — 자동 + 오버라이드 하이브리드
4.1 자동 생성 규칙
scpv2/resources/data/vpc.json을 읽어 다음과 같이 매핑:


service_name + method_name  →  도구 이름
  vpc.list_vpcs             →  scp_vpc_list_vpcs

params + required           →  JSON Schema (LLM이 검증)
  required: ["name", "cidr"]
  validation regex           →  schema.pattern

http_method                  →  annotations
  GET                        →  readOnlyHint=true
  POST/DELETE                →  destructiveHint=true
4.2 오버라이드 레이어 (tools.yaml)

scp_vpc_create_vpc:
  description: |
    SCP에 새 VPC를 생성합니다. CIDR은 사설 IP 대역(10.x, 172.16-31.x, 192.168.x) 사용.
  examples:
    - name: production-vpc
      cidr: 10.0.0.0/16
  destructive: true
  confirm_required: true     # confirm=true 안 보내면 거부
운영자가 LLM 친화적 설명을 점진적으로 추가할 수 있도록 분리.

5. 응답 슬리밍 정책
LLM 컨텍스트 보호가 핵심입니다. 모든 도구에 다음 공통 파라미터 자동 주입:

파라미터	기본	설명
max_items	50	리스트 응답 최대 항목 수 (Paginator로 모음)
fields	None	dot-path 필드 화이트리스트 (id,name,vpcState)
verbose	False	True면 ResponseMetadata 포함
기본 응답 변환 예시:


# raw
{"vpcs":[{...20개 필드}], "ResponseMetadata":{...}, "totalCount":42}
# shaped (default)
{"vpcs":[{id,name,vpcState,cidr} × 50], "totalCount":42, "_truncated":false}
6. 변경(Mutation) 작업 안전장치
세 단계의 가드레일:

policies.py의 read-only 모드 — env SCP_MCP_READONLY=true면 POST/DELETE/PUT 도구 자체를 등록하지 않음 (가장 강력)
destructiveHint=true MCP 어노테이션 → 클라이언트(Claude)가 사용자에게 추가 확인 받음
confirm=true 파라미터 강제 — confirm이 빠지면 ValidationError 반환 (이중 안전망)
7. Waiter는 별도 도구로 분리
블로킹 폴링을 MCP 한 요청 안에서 끝내면 안 됩니다. 다음 패턴:


scp_vpc_create_vpc(...)              # 즉시 반환 (id 포함)
scp_vpc_wait(id="...", state="ACTIVE", timeout=60)   # 별도 도구, 짧은 timeout
기본 timeout 60초, 상한 300초. 타임아웃 시 {"status":"pending","next":"call again"} 반환 → LLM이 재호출.

8. 에러 매핑
scpv2_mcp/errors.py에서 단일 변환기:


def to_mcp_error(exc) -> dict:
    if isinstance(exc, ValidationError):
        return {"error":"validation","message":str(exc)}
    if isinstance(exc, ClientError):
        return {"error":"api","code":exc.response.get("code"),
                "status":exc.status_code,"request_id":exc.request_id,
                "message":str(exc)}
    if isinstance(exc, WaiterError):
        return {"error":"timeout","waiter":exc.name,"message":str(exc)}
    if isinstance(exc, CredentialError):
        return {"error":"credential","message":"자격증명 확인 필요"}
    return {"error":"unknown","message":str(exc)}
모든 tool 함수를 @safe_call 데코레이터로 감싸 일관성 보장.

9. 단계적 로드맵
Phase	범위	산출물
P1 (MVP, 1~2일)	JSON→tool 자동등록, stdio 트랜스포트, read-only 모드, 기본 응답 슬리밍	scp_vpc_list_vpcs, scp_subnet_list_subnets 등 GET 계열 전체
P2 (안전한 쓰기)	destructive 어노테이션, confirm 강제, tools.yaml 오버라이드	create/delete 계열 활성화
P3 (다중 프로파일/Waiter)	profile 파라미터, wait 도구, audit log	운영 환경 사용 가능
P4 (확장)	HTTP/SSE 트랜스포트, MCP resources(scp://catalog/services), 캐싱, 복합 도구	외부 서비스로 노출
10. 주요 의사결정 포인트 (먼저 확인 필요)
진행 전에 결정해 주시면 좋은 항목:

타깃 클라이언트: Claude Code(stdio) / Claude Desktop / 둘 다 / 원격 HTTP?
읽기 전용으로 먼저? 아니면 변경 작업까지 한 번에?
자동생성 vs 손수 정의: 자동생성 메타프로그래밍이 부담스러우면 P1을 1:1 수동 매핑으로 시작 가능
fastmcp 버전: 2.x(최신) 사용? 의존성에 추가 필요
별도 패키지로 분리: scpv2-mcp라는 별도 pypi 패키지로 뺄지, 현 패키지의 optional extra로 둘지
어느 부분부터 착수할까요? 개인적으로는 "P1 자동생성 + read-only + main_mcp.py 데모" 까지 한 번에 만들어 SDK와 fastmcp의 결합이 실제로 깔끔하게 동작하는지 검증하는 것을 추천드립니다