"""
scpv2.exceptions — SCP SDK 예외 계층 (botocore.exceptions와 동일한 구조)
"""


class ScpError(Exception):
    """모든 SCP SDK 예외의 베이스 클래스"""


class ClientError(ScpError):
    """SCP API가 에러 응답을 반환했을 때 발생
    - response['code']    : 에러 코드 (예: 'ResourceNotFound')
    - response['message'] : 에러 메시지
    """
    def __init__(self, error_response: dict, operation_name: str):
        code = error_response.get("code", error_response.get("errorCode", "Unknown"))
        message = error_response.get("message", error_response.get("errorMessage", "Unknown"))
        super().__init__(
            f"An error occurred ({code}) when calling the "
            f"{operation_name} operation: {message}"
        )
        self.response = error_response
        self.operation_name = operation_name


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
