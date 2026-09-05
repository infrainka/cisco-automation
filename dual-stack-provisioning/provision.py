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

if not USERNAME or not PASSWORD:
    print("[-] CRITICAL: Missing ROUTER_USER or ROUTER_PASS in .env file.")
    sys.exit(1)

AUTH = (USERNAME, PASSWORD)
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json"
}

# Reading customer.yml for provisioning data
print("[*] Reading YAML configuration...")
try:
    with open("customer.yml", "r") as file:
        data = yaml.safe_load(file)["customer"]
except FileNotFoundError:
    print("[-] Error: customer.yml not found.")
    sys.exit(1)

print(f"[*] Provisioning Dual-Stack customer '{data['name']}' on {ROUTER_IP}...")

# Provision Dual-Stack VRF (IPv4 + IPv6)
vrf_url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native/vrf/definition"
vrf_payload = {
    "Cisco-IOS-XE-native:definition": [
        {
            "name": data["vrf_name"],
            "address-family": {
                "ipv4": {},
                "ipv6": {}
            }
        }
    ]
}

response_vrf = requests.patch(vrf_url, auth=AUTH, headers=HEADERS, json=vrf_payload, verify=False)
print(f"[*] Dual-Stack VRF Creation HTTP Status: {response_vrf.status_code}")

if response_vrf.status_code not in [200, 201, 204]:
    print(f"[-] VRF Creation Failed: {response_vrf.text}")
    sys.exit(1)

# Dual-stack subinterface provisioning
int_url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native/interface/GigabitEthernet"
subint_name = f"{data['interface']}.{data['vlan']}"

int_payload = {
    "Cisco-IOS-XE-native:GigabitEthernet": [
        {
            "name": subint_name,
            "encapsulation": {
                "dot1Q": {
                    "vlan-id": data["vlan"]
                }
            },
            "vrf": {
                "forwarding": data["vrf_name"]
            },
            "ip": {
                "address": {
                    "primary": {
                        "address": data["ipv4_address"],
                        "mask": data["ipv4_mask"]
                    }
                }
            },
            "ipv6": {
                "address": {
                    "prefix-list": [
                        {
                            "prefix": data["ipv6_prefix"]
                        }
                    ]
                }
            }
        }
    ]
}

response_int = requests.patch(int_url, auth=AUTH, headers=HEADERS, json=int_payload, verify=False)
print(f"[*] Subinterface Creation HTTP Status: {response_int.status_code}")

if response_int.status_code in [200, 201, 204]:
    print(f"[+] SUCCESS: Dual-Stack customer {data['name']} ({subint_name}) successfully provisioned!")
else:
    print(f"[-] Subinterface Creation Failed: {response_int.text}")
