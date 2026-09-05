import os
import sys
import yaml
import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

USERNAME = os.getenv("ROUTER_USER")
PASSWORD = os.getenv("ROUTER_PASS")
ROUTER_IP = os.getenv("ROUTER_IP")

if not all([USERNAME, PASSWORD, ROUTER_IP]):
    print("[-] CRITICAL: Missing credentials or IP in .env file.")
    sys.exit(1)

AUTH = (USERNAME, PASSWORD)
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json"
}

try:
    with open("qos_policy.yml", "r") as file:
        data = yaml.safe_load(file)["qos"]
except FileNotFoundError:
    print("[-] Error: qos_policy.yml not found.")
    sys.exit(1)

base_policy_url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native/policy"

# --- STEP 1: Provision Class-Maps ---
print(f"[*] Step 1: Provisioning Class-Maps...")
class_map_payload = {
    "Cisco-IOS-XE-native:policy": {
        "Cisco-IOS-XE-policy:class-map": [
            {
                "name": "CM-VOICE",
                "prematch": "match-any",
                "match": {"dscp": ["ef"]}
            },
            {
                "name": "CM-SCAVENGER",
                "prematch": "match-any",
                "match": {"dscp": ["cs1"]}
            }
        ]
    }
}
resp_cm = requests.patch(base_policy_url, auth=AUTH, headers=HEADERS, json=class_map_payload, verify=False)
if resp_cm.status_code not in [200, 201, 204]:
    print(f"[-] Class-Map Creation Failed (HTTP {resp_cm.status_code}): {resp_cm.text}")
    sys.exit(1)
print("[+] Class-Maps provisioned successfully.")


print(f"[*] Step 2: Provisioning Policy-Maps...")
policy_map_payload = {
    "Cisco-IOS-XE-native:policy": {
        "Cisco-IOS-XE-policy:policy-map": [
            {
                "name": "PM-EDGE-QOS",
                "class": [
                    {
                        "name": "CM-VOICE",
                        "action-list": [
                            {
                                "action-type": "priority",
                                "priority": {"percent": data["voice_percent"]}
                            }
                        ]
                    },
                    {
                        "name": "CM-SCAVENGER",
                        "action-list": [
                            {
                                "action-type": "bandwidth",
                                "bandwidth": {"percent": data["scavenger_percent"]}
                            }
                        ]
                    },
                    {
                        "name": "class-default",
                        "action-list": [
                            {"action-type": "fair-queue"},
                            {"action-type": "random-detect"}
                        ]
                    }
                ]
            },
            {
                "name": "PM-PARENT-SHAPER",
                "class": [
                    {
                        "name": "class-default",
                        "action-list": [
                            {
                                "action-type": "shape",
                                "shape": {
                                    "average": {"bit-rate": data["shaper_rate_bps"]}
                                }
                            },
                            {
                                "action-type": "service-policy",
                                "service-policy": "PM-EDGE-QOS"
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
resp_pm = requests.patch(base_policy_url, auth=AUTH, headers=HEADERS, json=policy_map_payload, verify=False)
if resp_pm.status_code not in [200, 201, 204]:
    print(f"[-] Policy-Map Creation Failed (HTTP {resp_pm.status_code}): {resp_pm.text}")
    sys.exit(1)
print("[+] Policy-Maps provisioned successfully.")


print(f"[*] Step 3: Attaching Service-Policy to {data['wan_interface']}...")
attach_url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native/interface/{data['wan_interface']}/Cisco-IOS-XE-policy:service-policy"
attach_payload = {
    "Cisco-IOS-XE-policy:service-policy": {
        "output": "PM-PARENT-SHAPER"
    }
}
resp_attach = requests.patch(attach_url, auth=AUTH, headers=HEADERS, json=attach_payload, verify=False)
if resp_attach.status_code in [200, 201, 204]:
    print("\n[✓] SUCCESS: QoS Policy successfully provisioned and attached via RESTCONF!")
else:
    print(f"[-] Policy Attachment Failed (HTTP {resp_attach.status_code}): {resp_attach.text}")
    sys.exit(1)