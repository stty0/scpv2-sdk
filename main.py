"""
main.py — 개발/테스트용 진입점 (패키지에 포함되지 않음)
"""
import scpv2

print("=== 방법 1: ~/.scp/credential.json 자동 로드 ===")
sess = scpv2.Session()
print(f"access_key  : {sess.credentials.access_key}")
print(f"region      : {sess.region}")
print(f"environment : {sess.environment}")
print(f"endpoint    : {sess.endpoint}")

print("\n=== SCP 인증 헤더 생성 ===")
ec2 = sess.client("ec2")
headers = ec2._get_headers(api_name="virtualserver", version="1.2")
for key, value in headers.items():
    print(f"  {key}: {value}")

print("\n=== 방법 2: 명시적 자격증명 ===")
sess2 = scpv2.Session(
    access_key="75874cea2857479c947a0bf41ced821c",
    secret_key="2388d32f-d63c-4ec8-8499-21974c506fae",
    region="kr-west1",
    environment="e",
)
print(f"endpoint : {sess2.endpoint}")
headers2 = sess2.client("ec2")._get_headers("virtualserver", "1.2")
print(f"  Scp-Accesskey  : {headers2['Scp-Accesskey']}")
print(f"  Scp-Signature  : {headers2['Scp-Signature']}")
print(f"  Scp-Timestamp  : {headers2['Scp-Timestamp']}")
print(f"  Scp-ClientType : {headers2['Scp-ClientType']}")
print(f"  Accept-Language: {headers2['Accept-Language']}")
print(f"  Scp-Api-Version: {headers2['Scp-Api-Version']}")

print("\n=== 방법 3: 환경변수 ===")
import os
os.environ["SCP_ACCESS_KEY"] = "env-access-key"
os.environ["SCP_SECRET_KEY"] = "env-secret-key"
os.environ["SCP_REGION"]     = "kr-east-1"

sess3 = scpv2.Session()
print(f"access_key : {sess3.credentials.access_key}")
print(f"region     : {sess3.region}")

print("\n=== 방법 4: 실제 SCP API 호출 (VPC 목록) ===")
try:
    vpc_client = sess.client("vpc")
    result = vpc_client.list_vpcs(size=20, page=0)
    print("VPC 목록:")
    print(result)
except Exception as e:
    print(f"API 호출 실패: {e}")
