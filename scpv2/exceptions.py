"""
scpv2.exceptions — SCP SDK 예외 계층
"""


class ScpError(Exception):
    """모든 SCP SDK 예외의 베이스 클래스"""


class ClientError(ScpError):
    """SCP API가 에러 응답을 반환했을 때 발생

    Attributes:
        response (dict):        원본 에러 응답 dict (_status, _body 항상 포함)
        operation_name (str):   호출한 메서드 이름
        status_code (int):      HTTP 상태 코드
    """

    # 단일 에러 객체에서 코드를 찾을 필드명 후보 (우선순위 순)
    _CODE_FIELDS    = ("code", "errorCode", "resultCode", "error", "title")
    # 단일 에러 객체에서 메시지를 찾을 필드명 후보
    _MESSAGE_FIELDS = ("detail", "message", "errorMessage", "resultDescription", "reason")

    def __init__(self, error_response: dict, operation_name: str):
        # SCP API: {"errors": [{...}]} 배열 형식 처리
        first_error = (error_response.get("errors") or [None])[0] or error_response

        code = next(
            (first_error[f] for f in self._CODE_FIELDS if first_error.get(f)),
            error_response.get("_status", "Unknown"),
        )
        message = next(
            (first_error[f] for f in self._MESSAGE_FIELDS if first_error.get(f)),
            error_response.get("_body", "Unknown"),
        )
        super().__init__(
            f"An error occurred ({code}) when calling the "
            f"{operation_name} operation: {message}"
        )
        self.response       = error_response
        self.operation_name = operation_name
        self.status_code    = first_error.get("status") or error_response.get("_status")
        self.request_id     = first_error.get("request_id") or first_error.get("global_request_id")


class ValidationError(ScpError):
    """파라미터 유효성 검사 실패 (API 호출 전 클라이언트 측 검사)"""


class CredentialError(ScpError):
    """자격증명을 찾을 수 없거나 형식이 잘못됐을 때 발생"""


class NoRegionError(ScpError):
    """region이 설정되지 않았을 때 발생"""


class WaiterError(ScpError):
    """Waiter가 최대 시도 횟수를 초과하거나 실패 상태에 진입했을 때 발생"""
    def __init__(self, name: str, reason: str):
        super().__init__(f"Waiter '{name}' failed: {reason}")
        self.name = name
        self.reason = reason


class PaginationError(ScpError):
    """페이지네이터 설정이 없거나 잘못됐을 때 발생"""
