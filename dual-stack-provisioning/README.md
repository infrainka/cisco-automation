# dual-stack-provisioning

Python/RESTCONF automation for provisioning customer-facing dual-stack (IPv4 + IPv6)
subinterfaces on Cisco IOS-XE, with a matching verification script for CI/CD gating.

## Contents

| File | Purpose |
|---|---|
| `customer.yml` | Declarative per-customer intent: name, physical interface, VLAN, VRF name, IPv4 address/mask, IPv6 prefix. |
| `provision.py` | PATCHes a dual-stack VRF (`address-family` ipv4 + ipv6) and an 802.1Q subinterface bound to that VRF, with the IPv4 primary address and IPv6 prefix from `customer.yml`. |
| `verify.py` | Read-only assertion suite: confirms the VRF has both address-families, and the subinterface's VLAN, VRF binding, IPv4 address, and IPv6 prefix all match `customer.yml`. Exit code 0/1 — usable as a CI/CD gate. |

## Prerequisites

```
pip install requests pyyaml python-dotenv urllib3
```

Create a `.env` file (not committed) in this directory:

```
ROUTER_IP=<router mgmt ip>
ROUTER_USER=<restconf user>
ROUTER_PASS=<restconf pass>
```

## Customer config

Each customer is one `customer.yml`. Example (placeholder data):

```yaml
customer:
  name: "Acme_Corp"
  interface: "0/0/1"
  vlan: 200
  vrf_name: "CUST_ACME"
  ipv4_address: "10.200.0.1"
  ipv4_mask: "255.255.255.0"
  ipv6_prefix: "2001:db8:200::1/64"
```

`interface` + `vlan` combine into the subinterface name (`GigabitEthernet{interface}.{vlan}`,
e.g. `GigabitEthernet0/0/1.200`).

## Run order

1. **Provision:**
   ```
   python provision.py
   ```
   Creates the VRF (dual-stack address-family) then the tagged subinterface — VRF first,
   since the subinterface PATCH binds `vrf forwarding` to it.

2. **Verify (CI gate):**
   ```
   python verify.py
   ```
   Confirms VRF address-families, VLAN encapsulation, VRF binding, IPv4 address, and IPv6
   prefix all match `customer.yml`; exits non-zero on any mismatch.

## Notes

- To onboard a new customer, copy `customer.yml` under a new name, fill in their values, and
  point `provision.py`/`verify.py` at it (currently both read `customer.yml` by filename —
  pass a path arg or swap the file per run until that's parameterized).
- Same namespace/schema caveats as `hsrp-qos` apply here (base path under
  `Cisco-IOS-XE-native:native`, `/` in interface names URL-encoded as `%2F` for GETs).