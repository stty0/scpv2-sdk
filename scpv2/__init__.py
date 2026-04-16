"""
scpv2 — Samsung SDS SCP v2 Python SDK

boto3와 동일한 개발자 경험을 제공하는 SCP(Samsung Cloud Platform) SDK입니다.

기본 사용법::

    import scpv2

    # 자격증명 자동 탐색 (환경변수 또는 ~/.scp/credential.json)
    sess = scpv2.Session()

    # ── client (저수준) ────────────────────────────────────────────────
    vpc_client = sess.client("vpc")
    result = vpc_client.list_vpcs(size=20, page=0)

    # ── Paginator ──────────────────────────────────────────────────────
    paginator = vpc_client.get_paginator("list_vpcs")
    for page in paginator.paginate(size=10):
        for vpc in page["contents"]:
            print(vpc)

    # ── Waiter ────────────────────────────────────────────────────────
    waiter = vpc_client.get_waiter("vpc_active")
    waiter.wait(id="vpc-abc123")

    # ── resource (고수준) + Collection ────────────────────────────────
    vpc = sess.resource("vpc")
    for v in vpc.vpcs.all():
        print(v)
    for v in vpc.vpcs.filter(vpcState="ACTIVE"):
        print(v)

    # ── 다중 프로파일 ──────────────────────────────────────────────────
    prod_sess = scpv2.Session(profile_name="prod")

    # ── 재시도 설정 ────────────────────────────────────────────────────
    from scpv2 import RetryConfig
    sess = scpv2.Session(retry_config=RetryConfig(max_attempts=5))
"""

from .session    import Session, Client, ServiceResource
from .retries    import RetryConfig
from .exceptions import (
    ScpError,
    ClientError,
    ValidationError,
    CredentialError,
    NoRegionError,
    WaiterError,
    PaginationError,
)
from . import resources  # 모든 서비스(vpc, virtualserver, s3, ...) 자동 등록

__all__ = [
    # 핵심 클래스
    "Session",
    "Client",
    "ServiceResource",
    "RetryConfig",
    # 예외
    "ScpError",
    "ClientError",
    "ValidationError",
    "CredentialError",
    "NoRegionError",
    "WaiterError",
    "PaginationError",
]

__version__ = "0.1.0"
