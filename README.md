# cisco-automation

Ansible + Python (RESTCONF) IaC for Cisco IOS-XE network automation — homelab and DevNet
Sandbox. Each subdirectory is a self-contained automation project with its own README,
playbooks/scripts, and inventory.

---

## Projects

| Directory | What it does | Stack |
|---|---|---|
| [`hsrp-qos/`](hsrp-qos/README.md) | First-hop redundancy (HSRP) on a Catalyst 3750-X and hierarchical MQC QoS (voice priority, scavenger class, parent shaper) on an ISR-4400, provisioned and verified via RESTCONF | Ansible (network_cli/paramiko), Python + `requests` |
| [`vpn-deploy/`](vpn-deploy/README.md) | IKEv2/IPsec remote-access VPN with full mutual PKI (certificate auth), licensing bootstrap, and NAT/pool config on a Cat8000v | Ansible, Cisco IOS-XE PKI/IKEv2 |
| [`dual-stack-provisioning/`](dual-stack-provisioning/README.md) | Customer-driven dual-stack (IPv4/IPv6) provisioning, with a declarative per-customer config and a matching verify script | Python + `requests` (RESTCONF) |

---

## Repository Structure

```
cisco-automation/
├── README.md
├── hsrp-qos/
│   ├── deploy_hsrp.yml
│   ├── discover_schema.py
│   ├── inventory.yml
│   ├── provision_qos.py
│   ├── qos_policy.yml
│   ├── README.md
│   └── verify_qos.py
├── vpn-deploy/
│   ├── ansible.cfg
│   ├── crypto_router.yml
│   ├── deploy_vpn.yml
│   ├── hosts.ini
│   ├── README.md
│   └── vault.yml
└── dual-stack-provisioning/
    ├── customer.yml
    ├── provision.py
    ├── README.md
    └── verify.py
```

---

## Credentials & Secrets

Each project keeps its own inventory/env pattern (see the project README for specifics),
but the rules are the same repo-wide:

- Real credentials never go in git — use Ansible Vault (`vault.yml`, AES-256 encrypted) or
  a local `.env` file, both covered by `.gitignore`.
- Files like `hosts.ini` / `inventory.yml` in this repo contain placeholders only; copy and
  fill in your own device details locally.
- `.gitignore` blocks `*.env`, `*.key`, `*.pem`, `secrets.yml`, and (deliberately, on top of
  the encrypted-is-fine convention some Ansible setups use) `vault.yml` itself — nothing
  with real secrets in it is meant to leave this machine.

## Prerequisites (common)

- Ansible >= 2.14, collection `cisco.ios` (`ansible-galaxy collection install -r requirements.yml` where present)
- Python 3, `requests`, `pyyaml`, `python-dotenv`, `urllib3`

See each project's README for device-specific requirements and run order.

## Lab Hardware

| Component | Detail |
|---|---|
| Core switch | Catalyst 3750-X, IOS 15.4 |
| WAN edge router | ISR-4400, IOS-XE 16.6 |
| VPN router | Cat8000v (DevNet Always-On Sandbox), IOS-XE 17.x |
| Physical lab | Cisco ISR 4451-X |
| Control node | Linux, Ansible + Python |