"""
scpv2.retries — 재시도 로직 (botocore.retries와 동일한 구조)

boto3 대응:
    RetryConfig  ←→ botocore.config.Config(retries={"max_attempts": 3, "mode": "standard"})
    RetryHandler ←→ botocore.retries.standard.StandardRetryHandler
"""
import random
import time

# 재시도 가능한 HTTP 상태 코드
RETRYABLE_STATUS_CODES: frozenset = frozenset({429, 500, 502, 503, 504})


class RetryConfig:
    """재시도 정책 설정

    Args:
        max_attempts: 최대 시도 횟수 (첫 시도 포함). 기본값 3.
        mode: 재시도 모드.
            - "standard": 지수 백오프 + 지터
            - "legacy":   고정 1초 대기
    """
    def __init__(self, max_attempts: int = 3, mode: str = "standard"):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.max_attempts = max_attempts
        self.mode = mode


class RetryHandler:
    """재시도 판단 및 백오프 대기 처리

    사용 예::

        handler = RetryHandler(RetryConfig(max_attempts=3))
        for attempt in range(handler.config.max_attempts):
            ...
            if handler.is_retryable(status_code):
                handler.backoff(attempt)
                continue
            break
    """

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()

    def is_retryable(self, status_code: int) -> bool:
        """해당 HTTP 상태 코드가 재시도 가능한지 여부 반환"""
        return status_code in RETRYABLE_STATUS_CODES

    def backoff(self, attempt: int):
        """재시도 전 대기

        standard 모드: min(2^attempt + random(0, 1), 20) 초
        legacy 모드:   1초 고정
        """
        if self.config.mode == "legacy":
            time.sleep(1)
        else:
            delay = min(2 ** attempt + random.uniform(0, 1), 20.0)
            time.sleep(delay)
