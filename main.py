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
    access_key="046d43fc60bf48fbb0d839e2e2711bef",
    secret_key="a13fe202-ce57-4db3-ba52-38898958e959",
    region="kr-west1",
    environment="s",
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