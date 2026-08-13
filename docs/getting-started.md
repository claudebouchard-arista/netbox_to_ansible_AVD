# Getting Started

## Prerequisites

- Python 3.10+
- Ansible Core 2.15+
- A running NetBox instance (v4.0+)
- [Arista AVD collection](https://avd.arista.com/) installed

```bash
pip install ansible-core pynetbox pyavd
ansible-galaxy collection install arista.avd
```

## Installation

```bash
ansible-galaxy collection install arista.netbox_avd
```

Or install from source:

```bash
cd ansible_collections/arista/netbox_avd
ansible-galaxy collection build
ansible-galaxy collection install arista-netbox_avd-*.tar.gz
```

## NetBox Setup

### 1. Create Custom Fields

The collection requires these custom fields in NetBox. Create them under **Customization > Custom Fields**:

| Name | Type | Object Types | Purpose |
|------|------|-------------|---------|
| `avd_node_id` | Integer | Device | Unique node ID for AVD IP addressing |
| `avd_node_group` | Text | Device | MLAG pair group name (e.g., `DC1_L3_LEAF1`) |
| `avd_bgp_as` | Integer | Device | BGP autonomous system number |
| `avd_vrf_vni` | Integer | VRF | VRF VNI for VXLAN |
| `avd_vtep_diagnostic_loopback` | Integer | VRF | Diagnostic loopback interface number |
| `avd_vtep_diagnostic_loopback_ip_range` | Text | VRF | Diagnostic loopback IP range |
| `avd_mac_vrf_vni_base` | Integer | Tenant | Base VNI for MAC VRFs |
| `avd_pool_role` | Text | Prefix | AVD pool role (`loopback`, `vtep`, `p2p_uplink`, `mlag_peer`, `mlag_peer_l3`) |

### 2. Populate NetBox

Create your fabric topology in NetBox:

1. **Site** -- one site per DC (e.g., `dc1`)
2. **Device roles** -- `spine`, `l3-leaf`, `l2-leaf`, `server`
3. **Devices** -- each switch with its role, site, and custom fields (`avd_node_id`, `avd_node_group`, `avd_bgp_as`)
4. **Management interfaces + IPs** -- `Management0` with an IP on each device
5. **Tenant** -- with `avd_mac_vrf_vni_base`
6. **VRFs** -- with `avd_vrf_vni` and diagnostic loopback custom fields
7. **VLANs** -- assigned to site and tenant
8. **Prefixes** -- one per VLAN (provides SVI gateway), plus IP pool prefixes tagged with `avd_pool_role`
9. **Servers** -- devices with role `server`, interfaces cabled to leaf switch ports
10. **Switch port config** -- set interface mode (access/tagged) and VLAN assignments

### 3. Create Your Site Directory

```bash
mkdir -p sites/dc1/avd_defaults

# Copy the example defaults as a starting point
cp ansible_collections/arista/netbox_avd/examples/single-dc-l3ls/avd_defaults/* \
   sites/dc1/avd_defaults/
```

Edit the defaults files to match your environment. See [Local Defaults](local-defaults.md) for what each file controls.

### 4. Create the Generate Playbook

```yaml title="sites/dc1/generate.yml"
---
- name: Generate AVD Inventory from NetBox for DC1
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    netbox_url: "{{ lookup('env', 'NETBOX_URL') }}"
    netbox_token: "{{ lookup('env', 'NETBOX_TOKEN') }}"
    netbox_site: dc1
    avd_defaults_dir: "{{ playbook_dir }}/avd_defaults"
    avd_output_dir: "{{ playbook_dir }}/avd_inventory"
  roles:
    - arista.netbox_avd.generate_avd
```

### 5. Generate and Build

```bash
# Step 1: Generate AVD inventory from NetBox
export NETBOX_URL=http://your-netbox:8000
export NETBOX_TOKEN=your-api-token
ansible-playbook sites/dc1/generate.yml

# Step 2: Review the generated files
ls sites/dc1/avd_inventory/group_vars/

# Step 3: Build EOS configs with AVD
cd sites/dc1/avd_inventory
ansible-playbook build.yml -i inventory.yml

# Step 4: Inspect generated configs
cat intended/configs/dc1-spine1.cfg
```

### 6. Commit the Output

```bash
git add sites/dc1/
git commit -m "Generate DC1 fabric from NetBox"
```

The committed output serves as both a reference and a CI golden-file. See [CI/CD & Verification](cicd.md).
