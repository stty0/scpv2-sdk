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
