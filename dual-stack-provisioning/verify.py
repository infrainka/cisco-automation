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
    print("[-] CRITICAL: Missing ROUTER_USER or ROUTER_PASS in .env")
    sys.exit(1)

AUTH = (USERNAME, PASSWORD)
HEADERS = {"Accept": "application/yang-data+json"}

# Load expected state from YAML
try:
    with open("customer.yml", "r") as f:
        expected = yaml.safe_load(f)["customer"]
except FileNotFoundError:
    print("[-] Error: customer.yml file not found.")
    sys.exit(1)

print(f"[*] Running Automated Assertion Suite for '{expected['name']}' on {ROUTER_IP}...")
errors = []

# Verify VRF Definition & Dual-Stack Address-Families
vrf_url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native/vrf/definition={expected['vrf_name']}"
resp_vrf = requests.get(vrf_url, auth=AUTH, headers=HEADERS, verify=False)

if resp_vrf.status_code == 200:
    vrf_data = resp_vrf.json().get("Cisco-IOS-XE-native:definition", {})
    af = vrf_data.get("address-family", {})
    if "ipv4" in af and "ipv6" in af:
        print(f"[+] PASS: VRF '{expected['vrf_name']}' exists with dual-stack address-families.")
    else:
        errors.append(f"VRF '{expected['vrf_name']}' missing dual-stack AF support.")
else:
    errors.append(f"VRF '{expected['vrf_name']}' query failed (HTTP {resp_vrf.status_code}).")

# verify subinterface operational state
subint = f"{expected['interface']}.{expected['vlan']}"
subint_encoded = subint.replace("/", "%2F")
int_url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native/interface/GigabitEthernet={subint_encoded}"
resp_int = requests.get(int_url, auth=AUTH, headers=HEADERS, verify=False)

if resp_int.status_code == 200:
    int_data = resp_int.json().get("Cisco-IOS-XE-native:GigabitEthernet", {})
    
    # Assert 802.1Q VLAN tagging
    vlan_id = int_data.get("encapsulation", {}).get("dot1Q", {}).get("vlan-id")
    if vlan_id == expected["vlan"]:
        print(f"[+] PASS: Encapsulation dot1Q VLAN matches {vlan_id}.")
    else:
        errors.append(f"VLAN mismatch: expected {expected['vlan']}, got {vlan_id}.")

    # Assert VRF binding
    vrf_bound = int_data.get("vrf", {}).get("forwarding")
    if vrf_bound == expected["vrf_name"]:
        print(f"[+] PASS: Interface bound to VRF '{vrf_bound}'.")
    else:
        errors.append(f"VRF binding mismatch: expected {expected['vrf_name']}, got {vrf_bound}.")

    # Primary IPv4 address
    ipv4_actual = int_data.get("ip", {}).get("address", {}).get("primary", {}).get("address")
    if ipv4_actual == expected["ipv4_address"]:
        print(f"[+] PASS: Primary IPv4 address matches {ipv4_actual}.")
    else:
        errors.append(f"IPv4 mismatch: expected {expected['ipv4_address']}, got {ipv4_actual}.")

    # IPv6 prefix list
    ipv6_prefixes = [
        p.get("prefix") 
        for p in int_data.get("ipv6", {}).get("address", {}).get("prefix-list", [])
    ]
    if expected["ipv6_prefix"] in ipv6_prefixes:
        print(f"[+] PASS: IPv6 prefix matches {expected['ipv6_prefix']}.")
    else:
        errors.append(f"IPv6 mismatch: expected {expected['ipv6_prefix']}, got {ipv6_prefixes}.")

else:
    errors.append(f"Subinterface {subint} not found on target device (HTTP {resp_int.status_code}).")

# Final CI/CD Gate Assessment
if not errors:
    print(f"\n[✓] VERIFICATION SUCCESSFUL: Target device state matches '{expected['name']}' specification.")
    sys.exit(0)
else:
    print("\n[✗] VERIFICATION FAILED:")
    for err in errors:
        print(f" - {err}")
    sys.exit(1)