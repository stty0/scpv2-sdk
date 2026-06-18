"""
main.py — 개발/테스트용 진입점 (패키지에 포함되지 않음)
"""
from __future__ import annotations
from typing import TYPE_CHECKING

import scpv2

if TYPE_CHECKING:
    from scpv2.stubs.vpc_client import VpcClient
    from scpv2.stubs.subnet_client import SubnetClient

sess = scpv2.Session(
    access_key="315d15c78c10482b964d06f07a0f1c3c",
    secret_key="82f18371-4222-454a-856e-ed69baf40368",
    region="kr-west1",
    environment="e"
)

vpc_client: VpcClient = sess.client("vpc")

result = vpc_client.list_vpcs(size=20, page=0)
print(result["vpcs"])
print()


subnet_client: SubnetClient = sess.client("subnet")
result = subnet_client.list_subnets()

# subnet_client.create_subnet(
#     name="publicSubnet",
#     cidr="192.168.10.0/24",
#     type="GENERAL",
#     vpc_id="5d9f027797ca4e20b68db1c652576347"
# )
print(result)