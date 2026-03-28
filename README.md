# cisco-automation

Ansible IaC for Cisco IOS-XE network automation — homelab and DevNet Sandbox.
Covers IKEv2/IPsec remote-access VPN deployment with full mutual PKI (certificate authentication),
licensing bootstrap, and supporting crypto infrastructure.

> **Status:** IKEv2 session verified UP-ACTIVE with mutual RSA authentication (AES-256-CBC / SHA-256 / DH group 14).

---

## Repository Structure

```
cisco-automation/
├── ansible.cfg          # Ansible runtime config (persistent connection, timeouts)
├── hosts.ini            # Inventory — fill in your device IP and credentials
├── vault.yml            # Ansible Vault — AES-256 encrypted credentials
├── deploy_vpn.yml       # Main playbook: full IKEv2 RA-VPN + PKI deployment
├── crypto_router.yml    # Bootstrap playbook: license activation + reload
├── requirements.yml     # Ansible collection dependencies
└── .gitignore
```

---

## Playbooks

### `deploy_vpn.yml` — IKEv2 Remote-Access VPN (Full Tunnel, Mutual PKI)

Full idempotent deployment of a remote-access IKEv2/IPsec VPN stack on Cisco IOS-XE.

**What it does:**

- Provisions a self-signed PKI trustpoint (`VPN-TP`) for the router's identity certificate
- Imports an external root CA (`HOMELAB-CA`) from a strongSwan-generated CA cert, with MD5 fingerprint pinning to bypass IOS-XE interactive prompts
- Configures IKEv2 proposal/policy (AES-256-CBC, SHA-256, DH group 14)
- Configures IKEv2 profile with mutual RSA-sig authentication — both peers present certificates, identity local set to `dn`
- Deploys a client IP pool, DNS push, and full-tunnel ACL via IKEv2 authorization policy
- Builds the IPsec transform-set and profile (ESP-AES-256 + ESP-SHA256-HMAC, tunnel mode)
- Attaches a Virtual-Template interface for VTI-based client termination
- Configures NAT exemption for VPN pool traffic and PAT overload on WAN

**Key variables** (override in `vault.yml` or `group_vars`):

| Variable | Default | Description |
|---|---|---|
| `vpn_trustpoint` | `VPN-TP` | Router PKI trustpoint name |
| `vpn_pool_name` | `RAVPN-POOL` | IKEv2 client IP pool name |
| `vpn_pool_start` | `10.10.10.10` | Pool range start |
| `vpn_pool_end` | `10.10.10.100` | Pool range end |
| `vpn_dns_primary` | `8.8.8.8` | Primary DNS pushed to clients |
| `vpn_dns_secondary` | `8.8.4.4` | Secondary DNS pushed to clients |
| `wan_interface` | `GigabitEthernet2` | Public-facing WAN interface |

---

### `crypto_router.yml` — License Bootstrap + Reload

One-shot playbook to activate `network-premier` and `dna-premier` license tier on IOS-XE, save the configuration, and issue a confirmed reload. Waits up to 10 minutes for the device to come back online. Run this once before `deploy_vpn.yml` if the device has not been licensed.

---

## PKI Architecture

```
HomeLab-Root-CA  (strongSwan, Linux control node)
├── Issues:  router identity cert  →  imported into VPN-TP trustpoint
└── CA cert: imported into HOMELAB-CA trustpoint on IOS-XE

VPN-TP  (Cisco IOS-XE)
└── Router certificate signed by HomeLab-Root-CA
    CN=vpn.homelab.local
    hostname=cat8000v.cisco.com
    Valid: 2026-03-28 → 2036-03-25

strongSwan client (Teknotaivas)
└── Client certificate signed by HomeLab-Root-CA
```

Both peers authenticate with RSA signatures. The router identity is `dn` (Distinguished Name from the certificate subject). The CA cert is shared and trusted on both sides.

---

## PKI Deployment Notes

The Ansible `crypto pki enroll VPN-TP` task originally generated a self-signed certificate.
The final working configuration uses a **CA-signed router certificate** imported via `crypto pki import VPN-TP certificate` after submitting the CSR to the strongSwan CA on the control node.

The IKEv2 profile was also corrected post-playbook:

- `identity local fqdn vpn.homelab.local` replaced with `identity local dn`
- Both `VPN-TP` (signing) and `HOMELAB-CA` (verification) trustpoints confirmed active

These corrections will be folded back into the playbook in a future iteration.

---

## Verified Session Output

```
Session-id:6, Status:UP-ACTIVE, IKE count:1, CHILD count:1

Tunnel-id  Local              Remote               Status
2          10.10.20.48/4500   <CLIENT_IP>/48082     READY

Encr: AES-CBC, keysize: 256
PRF:  SHA256
Hash: SHA256
DH:   Group 14
Auth sign:   RSA
Auth verify: RSA
Life/Active Time: 86400/931 sec
```

---

## Prerequisites

- Ansible >= 2.14
- Collections: `cisco.ios`, `ansible.netcommon`, `ansible.utils`
- `openssl` available on the control node (used for CA MD5 fingerprint extraction)
- strongSwan CA certificate present on the control node at `/etc/ipsec.d/cacerts/strongswanCaCert.pem`

Install collections:

```bash
ansible-galaxy collection install -r requirements.yml
```

---

## Usage

```bash
# Run once to activate licensing before first VPN deployment
ansible-playbook crypto_router.yml --ask-vault-pass

# Deploy full IKEv2 VPN stack
ansible-playbook deploy_vpn.yml --ask-vault-pass
```

---

## Inventory Setup

`hosts.ini` in this repository contains only placeholders. Copy and fill in your device details before running any playbook. Store real credentials in Ansible Vault — never commit plaintext passwords.

```ini
[sandbox_devices]
<DEVICE_IP>

[sandbox_devices:vars]
ansible_connection=network_cli
ansible_network_os=cisco.ios.ios
ansible_user=<USERNAME>
ansible_password=<VAULT_VAR>
ansible_become=yes
ansible_become_method=enable
ansible_become_password=<VAULT_VAR>
```

---

## Security Notes

- `vault.yml` is AES-256 encrypted — **never commit the plaintext version**
- `hosts.ini` in this repository contains only placeholders — store real credentials in Ansible Vault
- The self-signed trustpoint and CA fingerprint pinning are appropriate for lab environments; production deployments should use a proper PKI hierarchy with a trusted CA
- The `HOMELAB-CA` trustpoint uses `revocation-check none` — add CRL or OCSP for production use

---

## Lab Environment

| Component | Detail |
|---|---|
| Router | Cisco Cat8000v (DevNet Always-On Sandbox) |
| IOS-XE | 17.x |
| Control node | Linux, Ansible (Teknotaivas) |
| VPN client | strongSwan, IKEv2 with mutual certificate authentication |
| Physical lab | Cisco ISR 4451-X |