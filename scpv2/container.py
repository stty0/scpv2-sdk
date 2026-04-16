from . import resources  # 리소스 등록 트리거 (Session 레지스트리에 서비스 등록)
from .session import Session

_session = None


def get_session() -> Session:
    """전역 Session 싱글톤 반환
    자격증명 우선순위: explicit → 환경변수 → ~/.scp/credential.json
    """
    global _session
    if _session is None:
        _session = Session()  # 자격증명은 CredentialResolver가 자동 탐색
    return _session
