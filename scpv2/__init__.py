"""
scpv2 — Samsung SDS SCP v2 Python SDK

boto3와 동일한 개발자 경험을 제공하는 SCP(Samsung Cloud Platform) SDK입니다.

기본 사용법::

    import scpv2

    # 자격증명 자동 탐색 (환경변수 또는 ~/.scp/credential.json)
    sess = scpv2.Session()
    vpc_client = sess.client("vpc")
    result = vpc_client.list_vpcs(size=20, page=0)

    # 명시적 자격증명
    sess = scpv2.Session(
        access_key="YOUR_ACCESS_KEY",
        secret_key="YOUR_SECRET_KEY",
        region="kr-west1",
    )
"""

from .session import Session, Client, ServiceResource
from . import resources  # 모든 서비스(ec2, s3, vpc, ...) 자동 등록

__all__ = [
    "Session",
    "Client",
    "ServiceResource",
]

__version__ = "0.1.0"
