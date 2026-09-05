import os
import sys
import requests
import json
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

USERNAME = os.getenv("ROUTER_USER")
PASSWORD = os.getenv("ROUTER_PASS")
ROUTER_IP = os.getenv("ROUTER_IP")

AUTH = (USERNAME, PASSWORD)
HEADERS = {"Accept": "application/yang-data+json"}

print(f"[*] Querying the policy container on {ROUTER_IP}...")

# Querying the policy container to see how the router formats the data
url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native/policy"

response = requests.get(url, auth=AUTH, headers=HEADERS, verify=False)

if response.status_code == 200:
    print("\n[+] SUCCESS! Here is the exact JSON structure the router expects:\n")
    print(json.dumps(response.json(), indent=4))
elif response.status_code == 404:
    print("[-] 404 Not Found: The 'policy' container doesn't exist at this URL.")
    print("[*] Try querying the base native container instead...")
    
    # Fallback to query the root native container with a depth limit
    fallback_url = f"https://{ROUTER_IP}/restconf/data/Cisco-IOS-XE-native:native?content=config&depth=3"
    fallback_resp = requests.get(fallback_url, auth=AUTH, headers=HEADERS, verify=False)
    
    if fallback_resp.status_code == 200:
        print("\n[*] Root configuration fetched. Look for 'policy' or 'class-map' in this output:\n")
        print(json.dumps(fallback_resp.json(), indent=4))
else:
    print(f"[-] Query failed (HTTP {response.status_code}): {response.text}")
