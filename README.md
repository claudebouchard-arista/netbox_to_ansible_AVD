# arista.netbox_avd

Generate [Arista AVD](https://avd.arista.com/) inventory from [NetBox](https://netbox.dev/) as source of truth.

This Ansible collection queries NetBox for your DC/campus fabric topology and produces ready-to-run AVD inventory files. A human can review and optionally edit the generated YAML, then run AVD to build EOS device configurations.

## Pipeline

```
NetBox (devices, IPs, VLANs, VRFs, cables, ASNs, IP pools)
  +
Local YAML Defaults (passwords, STP, interface patterns)
  ↓
generate_avd role → AVD inventory (inventory.yml + group_vars/)
  ↓
human review (optional)
  ↓
AVD build.yml → EOS configs (.cfg per device)
```

**Decoupled by design** — once generated, the AVD inventory is standalone. NetBox is not needed to build or deploy configs.

## Supported Topologies

| Topology | Site Example | Devices | Description |
|----------|-------------|---------|-------------|
| **Single-DC L3LS** | `sites/dc1/` | 8 | BGP EVPN/VXLAN with MLAG leaf pairs |
| **Dual-DC L3LS** | `sites/dual-dc/` | 16 | Two DCs with DCI inter-connect links |
| **L2LS** | `sites/l2ls/` | 6 | Pure L2 fabric, MLAG everywhere, no BGP |
| **Campus** | `sites/campus/` | 7 | OSPF routing on spines, IDF leaf hierarchy |

## What Comes From NetBox

| Data | NetBox Object |
|------|--------------|
| Devices, roles, management IPs | `dcim.devices` + `ipam.ip-addresses` |
| BGP AS numbers | Custom field `avd_bgp_as` on devices |
| MLAG pairs / node groups | Custom field `avd_node_group` on devices |
| Node IDs | Custom field `avd_node_id` on devices |
| IP pools (loopback, VTEP, P2P, MLAG) | `ipam.prefixes` with `avd_pool_role` |
| Tenants | `tenancy.tenants` with `avd_mac_vrf_vni_base` |
| VRFs + VNIs | `ipam.vrfs` with `avd_vrf_vni` |
| VLANs → SVIs + L2 VLANs | `ipam.vlans` + `ipam.prefixes` |
| SVI virtual gateways | Derived from prefix (.1 address) |
| Server connections | `dcim.cables` + interface mode/VLANs |
| Port-channels | Interface LAG membership |

## What Stays in Local YAML

Passwords, AAA users, DNS/NTP, spanning tree settings, interface naming patterns, virtual router MAC — things that are AVD-specific and don't belong in NetBox.

## Prerequisites

- Python 3.10+
- Ansible Core 2.15+
- Docker & Docker Compose (for development/testing)
- NetBox v4.0+ with custom fields configured ([see docs](https://claudebouchard-arista.github.io/netbox_to_ansible_AVD/netbox-data-model/))
- [Arista AVD](https://avd.arista.com/) collection (`pip install "pyavd[ansible]"`)

## Quick Start

```bash
# 1. Install
pip install ansible-core pyavd
ansible-galaxy collection install arista.avd arista.netbox_avd

# 2. Set up your site
mkdir -p sites/mysite/avd_defaults
cp examples/single-dc-l3ls/avd_defaults/* sites/mysite/avd_defaults/
# Edit defaults for your environment

# 3. Create generate.yml
cat > sites/mysite/generate.yml << 'EOF'
---
- name: Generate AVD from NetBox
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    netbox_url: "{{ lookup('env', 'NETBOX_URL') }}"
    netbox_token: "{{ lookup('env', 'NETBOX_TOKEN') }}"
    netbox_site: mysite
    avd_defaults_dir: "{{ playbook_dir }}/avd_defaults"
    avd_output_dir: "{{ playbook_dir }}/avd_inventory"
  roles:
    - arista.netbox_avd.generate_avd
EOF

# 4. Generate + build
export NETBOX_URL=http://your-netbox:8000 NETBOX_TOKEN=your-token
ansible-playbook sites/mysite/generate.yml
cd sites/mysite/avd_inventory
ansible-playbook build.yml -i inventory.yml

# 5. Inspect configs
ls intended/configs/
```

For multi-DC, use `netbox_sites: [dc1, dc2]` instead of `netbox_site`.

For L2LS or campus, override `avd_role_mapping` and `avd_group_config` — see `sites/l2ls/generate.yml` and `sites/campus/generate.yml` for examples.

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `netbox_url` | `$NETBOX_URL` | NetBox API URL |
| `netbox_token` | `$NETBOX_TOKEN` | NetBox API token |
| `netbox_site` | `""` | Single site slug to generate |
| `netbox_sites` | `[]` | List of site slugs (multi-DC) |
| `avd_defaults_dir` | `{{ playbook_dir }}/avd_defaults` | Path to local YAML defaults |
| `avd_output_dir` | `{{ playbook_dir }}/avd_inventory` | Where to write generated files |
| `avd_role_mapping` | `{spine: spine, l3-leaf: l3leaf, l2-leaf: l2leaf}` | NetBox role slug → AVD type |
| `avd_group_config` | `{}` | Override inventory group naming (for L2LS/campus) |
| `avd_node_id_field` | `avd_node_id` | Custom field name for node ID |
| `avd_node_group_field` | `avd_node_group` | Custom field name for MLAG group |
| `avd_generate_playbooks` | `true` | Generate build.yml and deploy.yml |

## Devcontainer

This repo includes a devcontainer with all dependencies. Docker ports are dynamically allocated to avoid conflicts — `make up` prints the NetBox URL.

## Development

```bash
make help              # Show all targets

# NetBox
make up                # Start NetBox (Docker)
make down              # Stop NetBox
make seed              # Seed DC1
make seed-dual         # Seed DC1 + DC2
make seed-l2ls         # Seed L2LS site
make seed-campus       # Seed campus site
make seed-all          # Seed everything

# Generate
make generate          # Generate + AVD build all sites
make verify            # Regenerate + diff against committed reference

# Test
make lint              # flake8 + yamllint
make test-unit         # 64 unit tests
make test-integration  # 17 integration tests against live NetBox
make build             # Build collection tarball
```

## CI/CD

Every PR runs lint, unit tests, and integration tests. The integration pipeline seeds a fresh NetBox, generates all sites, runs AVD build, and diffs the output against committed reference files — if anything drifts, CI fails with the exact diff.

## Documentation

Full docs at **https://claudebouchard-arista.github.io/netbox_to_ansible_AVD/**

## Sister Projects

- [netbox_to_ansible_velocloud](https://github.com/claudebouchard-arista/netbox_to_ansible_velocloud) — NetBox → VeloCloud SD-WAN
- [netbox_to_ansible_cvcue](https://github.com/claudebouchard-arista/netbox_to_ansible_cvcue) — NetBox → CV-CUE WiFi

## License

Apache-2.0
