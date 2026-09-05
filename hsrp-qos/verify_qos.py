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
    print("[-] CRITICAL: Missing ROUTER_USER, ROUTER_PASS, or ROUTER_IP in .env")
    sys.exit(1)

AUTH = (USERNAME, PASSWORD)
HEADERS = {"Accept": "application/yang-data+json"}

# Load expected state from YAML
try:
    with open("qos_policy.yml", "r") as f:
        expected = yaml.safe_load(f)["qos"]
except FileNotFoundError:
    print("[-] Error: qos_policy.yml file not found.")
    sys.exit(1)

print(f"[*] Running Automated Assertion Suite for QoS Policy on {ROUTER_IP}...")
errors = []

# Verify Service-Policy Attachment
attach_url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native/interface/{expected['wan_interface']}/Cisco-IOS-XE-policy:service-policy"
resp_attach = requests.get(attach_url, auth=AUTH, headers=HEADERS, verify=False)

if resp_attach.status_code == 200:
    sp_data = resp_attach.json().get("Cisco-IOS-XE-policy:service-policy", {})
    output_policy = sp_data.get("output")
    
    if output_policy == "PM-PARENT-SHAPER":
        print(f"[+] PASS: Service-policy 'PM-PARENT-SHAPER' is attached outbound on {expected['wan_interface']}.")
    else:
        errors.append(f"Service-policy mismatch: expected 'PM-PARENT-SHAPER', got '{output_policy}'.")
else:
    errors.append(f"Failed to fetch service-policy on interface (HTTP {resp_attach.status_code}).")

# Verify Shaping Rate in Policy-Map
pm_url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native/policy/Cisco-IOS-XE-policy:policy-map=PM-PARENT-SHAPER"
resp_pm = requests.get(pm_url, auth=AUTH, headers=HEADERS, verify=False)

if resp_pm.status_code == 200:
    pm_response = resp_pm.json().get("Cisco-IOS-XE-policy:policy-map", [])
    pm_data = pm_response[0] if isinstance(pm_response, list) and len(pm_response) > 0 else pm_response
    
    classes = pm_data.get("class", [])
    shaper_found = False
    
    for c in classes:
        if c.get("name") == "class-default":
            # Iterate through the action-list to find the shape action
            for action in c.get("action-list", []):
                if action.get("action-type") == "shape":
                    bit_rate = action.get("shape", {}).get("average", {}).get("bit-rate")
                    if bit_rate == expected["shaper_rate_bps"]:
                        print(f"[+] PASS: Shaper bit-rate accurately matches {expected['shaper_rate_bps']} bps.")
                        shaper_found = True
                    else:
                        errors.append(f"Shaper rate mismatch: expected {expected['shaper_rate_bps']}, got {bit_rate}.")
                        shaper_found = True
    
    if not shaper_found:
        errors.append("Could not find 'shape' action in 'PM-PARENT-SHAPER'.")
else:
    errors.append(f"Failed to fetch policy-map 'PM-PARENT-SHAPER' (HTTP {resp_pm.status_code}).")

# Final CI/CD Gate Assessment
if not errors:
    print(f"\n[✓] VERIFICATION SUCCESSFUL: QoS configuration matches specification.")
    sys.exit(0)
else:
    print("\n[✗] VERIFICATION FAILED:")
    for err in errors:
        print(f" - {err}")
    sys.exit(1)
