"""
scpv2.response — HTTP 응답을 ResponseMetadata가 포함된 dict로 변환

모든 성공 응답에 ResponseMetadata가 포함됩니다::

    {
        "contents": [...],          # 실제 데이터
        "ResponseMetadata": {
            "RequestId":     "abc-123",
            "HTTPStatusCode": 200,
            "HTTPHeaders":   {...},
            "RetryAttempts":  0,
        }
    }
"""
from __future__ import annotations


def build_response(data: dict, http_response, retry_attempts: int = 0) -> dict:
    """API 응답 dict에 ResponseMetadata를 추가하여 반환

    Args:
        data:           파싱된 JSON 응답 데이터
        http_response:  requests.Response 객체
        retry_attempts: 실제 재시도 횟수
    """
    headers = dict(http_response.headers)
    request_id = (
        headers.get("x-scp-request-id")
        or headers.get("x-request-id")
        or headers.get("x-amzn-requestid")
        or ""
    )
    return {
        **data,
        "ResponseMetadata": {
            "RequestId":      request_id,
            "HTTPStatusCode": http_response.status_code,
            "HTTPHeaders":    headers,
            "RetryAttempts":  retry_attempts,
        },
    }
