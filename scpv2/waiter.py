"""
scpv2.waiter — 웨이터 (boto3.waiters와 동일한 구조)

boto3 대응:
    Waiter ←→ botocore.waiter.Waiter

JSON 서비스 정의 스키마::

    "waiters": {
        "vpc_active": {
            "operation":    "list_vpcs",    # 폴링에 사용할 Client 메서드 이름
            "delay":        5,              # 시도 간격 (초)
            "max_attempts": 20,            # 최대 시도 횟수
            "acceptors": [
                {
                    "matcher":  "path",            # "path" | "status"
                    "argument": "contents[0].vpcState",  # path 표현식
                    "expected": "ACTIVE",          # 기대값
                    "state":    "success"          # "success" | "failure"
                },
                {
                    "matcher":  "path",
                    "argument": "contents[0].vpcState",
                    "expected": "ERROR",
                    "state":    "failure"
                }
            ]
        }
    }

사용 예::

    waiter = vpc_client.get_waiter("vpc_active")
    waiter.wait(id="vpc-abc123")          # ACTIVE 상태가 될 때까지 폴링
"""
from __future__ import annotations

import re
import time
from typing import Any

from .exceptions import WaiterError


def _resolve_path(data: Any, path: str) -> Any:
    """간단한 경로 표현식 리졸버

    지원 형식:
        - ``key``               단순 키
        - ``parent.child``      중첩 키
        - ``list[0]``           인덱스 접근
        - ``list[0].field``     인덱스 + 중첩 키

    Args:
        data: 탐색할 dict 또는 list
        path: 점(.)으로 구분된 경로 문자열

    Returns:
        경로가 가리키는 값. 경로가 존재하지 않으면 None.
    """
    parts = re.split(r"\.", path)
    current = data
    for part in parts:
        if current is None:
            return None
        m = re.match(r"^(\w+)\[(\d+)\]$", part)
        if m:
            key, idx = m.group(1), int(m.group(2))
            lst = current.get(key, []) if isinstance(current, dict) else []
            current = lst[idx] if idx < len(lst) else None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


class Waiter:
    """리소스가 특정 상태가 될 때까지 폴링하는 웨이터

    boto3와 동일하게 client.get_waiter(waiter_name)으로 획득합니다.
    """

    def __init__(self, name: str, config: dict, client):
        self.name = name
        self._config = config
        self._client = client

    def wait(self, **kwargs):
        """리소스가 success 상태 acceptor를 만족할 때까지 폴링

        Args:
            **kwargs: 폴링에 사용할 operation의 파라미터

        Raises:
            WaiterError: failure 상태에 진입하거나 max_attempts를 초과한 경우
        """
        operation    = self._config["operation"]
        delay        = self._config.get("delay", 5)
        max_attempts = self._config.get("max_attempts", 20)
        acceptors    = self._config.get("acceptors", [])

        method = getattr(self._client, operation)

        for attempt in range(1, max_attempts + 1):
            try:
                response = method(**kwargs)
            except Exception as exc:
                response = {}
                # error acceptor 체크 (status matcher)
                for acceptor in acceptors:
                    if acceptor.get("matcher") == "error":
                        if acceptor["expected"] in str(exc):
                            if acceptor["state"] == "success":
                                return
                            raise WaiterError(self.name, str(exc))

            for acceptor in acceptors:
                if self._matches(response, acceptor):
                    state = acceptor["state"]
                    if state == "success":
                        return
                    raise WaiterError(
                        self.name,
                        f"Resource entered failure state (acceptor: {acceptor})"
                    )

            if attempt < max_attempts:
                time.sleep(delay)

        raise WaiterError(
            self.name,
            f"Max attempts ({max_attempts}) exceeded"
        )

    # ── 내부 헬퍼 ──────────────────────────────────────────────────────────

    def _matches(self, response: dict, acceptor: dict) -> bool:
        matcher  = acceptor.get("matcher", "path")
        expected = acceptor["expected"]

        if matcher == "path":
            value = _resolve_path(response, acceptor["argument"])
            return value == expected

        if matcher == "status":
            status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            return status == expected

        return False
