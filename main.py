"""
main.py — 개발/테스트용 진입점 (패키지에 포함되지 않음)
"""
import scpv2

sess = scpv2.Session(
    access_key="75874cea2857479c947a0bf41ced821c",
    secret_key="2388d32f-d63c-4ec8-8499-21974c506fae",
    region="kr-west1",
    environment="e",
)

# ── 방법 1: client (저수준) ────────────────────────────────
print("=== client 방식 ===")
vpc_client = sess.client("vpc")
try:
    vpc_client.create_subnet()
except  AttributeError as e:
    pass
result = vpc_client.list_vpcs(size=20, page=0)
print(result)

# ── 방법 2: resource (고수준) ──────────────────────────────
print("\n=== resource 방식 ===")
vpc = sess.resource("vpc")
result = vpc.list(size=20, page=0)   # list_vpcs 로 위임
print(result)

# resource로 생성/삭제도 동일하게 가능
# vpc.create(name="my-vpc", cidr="10.0.0.0/24")
# vpc.delete(vpc_id="...")

# ── VPC 삭제 ────────────────────────────────
# try:
#     vpc_client.delete_vpc(vpc_id="9b82587f27ca4d5db67bf40b01740f83")
# except scpv2.ClientError as e:
#     print(e.status_code)   # 404
#     print(e.request_id)    # req-3cbc1905-...
#     if e.response["errors"][0]["code"] == "ResourceNotFound":
#         print("VPC가 존재하지 않습니다.")

result = vpc_client.list_vpcs()
print(result)  # 원본 응답 전체 출력

# collection으로 확인
items = list(vpc.vpcs.all())
print(f"총 {len(items)}개")


# 전체 순회
for v in vpc.vpcs.all():
    print(v["state"])

vpc.vpcs.all()

paginator = vpc_client.get_paginator("list_vpcs")
for page in paginator.paginate(size=10):
    for vpc in page["vpcs"]:
        print(vpc["name"])

# 전체 결과를 한 번에 수집
result = paginator.paginate(size=10).build_full_result()
all_vpcs = result["vpcs"]
print(all_vpcs)