# Cisco YANG/RESTCONF Lab — First-Hop Redundancy & Model-Driven QoS

Automated, version-controlled provisioning for HSRP (Catalyst 3750-X, Ansible/SSH)
and hierarchical MQC QoS (ISR-4400, RESTCONF/Python). Companion code for the writeup:
[Reverse-Engineering Cisco YANG Models (again)](https://blog.bittiviidakon.fi/en/2026/09/05/reverse-engineering-cisco-yang-models-again-implementing-first-hop-redundancy-and-qos/).

## Topology

- **L3 switch** — Catalyst 3750-X, IOS 15.4. No RESTCONF/NETCONF support → managed via
  Ansible `network_cli` over SSH (paramiko).
- **WAN edge router** — ISR-4400, IOS-XE 16.6. Managed via RESTCONF (`Cisco-IOS-XE-native`
  model, `Cisco-IOS-XE-policy` augmentation).

## Files

| File | Target | Purpose |
|---|---|---|
| `inventory.yml` | switch + router | Ansible inventory. Credentials pulled from environment via `lookup('env', ...)`. |
| `deploy_hsrp.yml` | l3_switch | Configures HSRP on Vlan10/Vlan20 (priority 150, preempt, MD5 auth). |
| `discover_schema.py` | isr4400 | GETs the live `policy` container to reverse-engineer the exact JSON shape IOS-XE expects before writing PATCH payloads. Run this first when a model changes. |
| `provision_qos.py` | isr4400 | PATCHes class-maps (`CM-VOICE`, `CM-SCAVENGER`), policy-maps (`PM-EDGE-QOS`, `PM-PARENT-SHAPER`), then attaches the shaper outbound on the WAN interface. |
| `qos_policy.yml` | — | Declarative QoS intent consumed by `provision_qos.py` / `verify_qos.py` (voice %, scavenger %, shaper rate, WAN interface). |
| `verify_qos.py` | isr4400 | Read-only assertion suite: confirms service-policy attachment and shaper bit-rate match `qos_policy.yml`. Exit code 0/1 — usable as a CI/CD gate. |

## Prerequisites

```
pip install requests pyyaml python-dotenv urllib3
pip install ansible
ansible-galaxy collection install cisco.ios
```

Create a `.env` file (not committed) in this directory:

```
ROUTER_IP=<router mgmt ip>
ROUTER_USER=<restconf user>
ROUTER_PASS=<restconf pass>
SWITCH_IP=<switch mgmt ip>
SWITCH_USER=<ssh user>
SWITCH_PASS=<ssh pass>
HSRP_KEY=<hsrp md5 key-string>
```

## Run order

1. **HSRP (switch, Ansible):**
   ```
   ansible-playbook -i inventory.yml deploy_hsrp.yml
   ```
   Requires a physical interface up in each VLAN — 3750-X SVI autostate is hardcoded in
   ASIC and can't be disabled in software, so HSRP will sit in `Init` until a port in
   that VLAN is `up/up`.

2. **Schema discovery (router, as needed):** `python discover_schema.py`
   Only needed when probing an unfamiliar/updated YANG model before writing a new payload.

3. **QoS provisioning (router):** `python provision_qos.py`
   Creates class-maps → policy-maps → attaches `PM-PARENT-SHAPER` outbound.

4. **Verification (router, CI gate):** `python verify_qos.py`
   Confirms the config matches `qos_policy.yml`; exits non-zero on mismatch.

## Key gotchas (from this lab)

- **SSH ciphers:** modern OpenSSH refuses `hmac-sha1`/`ssh-rsa` from old IOS — set
  `ansible_network_cli_ssh_type: paramiko` in inventory.
- **SVI autostate:** can't be turned off on 3750-X; needs a live physical port in the VLAN.
- **RESTCONF namespaces:** payload keys need the `Cisco-IOS-XE-policy:` prefix even though
  the base path is under `Cisco-IOS-XE-native:native/policy` — discovered via
  `discover_schema.py`, not documentation.
- **MQC actions** (`priority`, `bandwidth`, `shape`) must sit inside an `action-list` array,
  not as direct keys under a class.
- **Interface names in URLs** need `/` URL-encoded as `%2F` (see `wan_interface` in
  `qos_policy.yml`).

## Note

`deploy_hsrp.yml` reads the HSRP MD5 key from `HSRP_KEY` in `.env` (falls back to
`CHANGE_ME` if unset) instead of a hardcoded string, so it's safe to push publicly.