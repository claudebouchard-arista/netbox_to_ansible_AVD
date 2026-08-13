# NetBox Data Model

This page describes everything you need to set up in NetBox for the collection to generate a complete AVD inventory.

## Custom Fields

These custom fields must be created in NetBox before using the collection:

### On Devices (`dcim.device`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `avd_node_id` | Integer | Yes | Unique node ID used by AVD for IP addressing algorithms. Must be unique within each node type. |
| `avd_node_group` | Text | For leafs | Node group name for MLAG pairs. Two devices with the same group name form an MLAG pair. Leave empty for spines. |
| `avd_bgp_as` | Integer | For BGP devices | BGP AS number. All devices in an MLAG pair should have the same AS. |

### On VRFs (`ipam.vrf`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `avd_vrf_vni` | Integer | Yes | VRF VNI for VXLAN routing |
| `avd_vtep_diagnostic_loopback` | Integer | No | Loopback interface number for VTEP diagnostics |
| `avd_vtep_diagnostic_loopback_ip_range` | Text | No | IP range for diagnostic loopbacks (e.g., `10.255.10.0/27`) |

### On Tenants (`tenancy.tenant`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `avd_mac_vrf_vni_base` | Integer | Yes | Base VNI number. Each VLAN's VNI = base + VLAN ID |

### On Prefixes (`ipam.prefix`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `avd_pool_role` | Text | For pool prefixes | One of: `loopback`, `vtep`, `p2p_uplink`, `mlag_peer`, `mlag_peer_l3` |

## Device Roles

Create these device roles (the slug must match exactly):

| Role Name | Slug | AVD Type | Description |
|-----------|------|----------|-------------|
| Spine | `spine` | `spine` | Spine switches |
| L3 Leaf | `l3-leaf` | `l3leaf` | L3 leaf switches (EVPN/VXLAN) |
| L2 Leaf | `l2-leaf` | `l2leaf` | L2 leaf switches |
| Server | `server` | -- | Connected endpoints (servers, firewalls, etc.) |

!!! tip "Custom role mapping"
    If your NetBox uses different role slugs, configure `avd_role_mapping` in your playbook vars:
    ```yaml
    avd_role_mapping:
      my-spine-role: spine
      my-leaf-role: l3leaf
      my-access-role: l2leaf
    ```

## IP Pool Prefixes

Create these prefixes in your site with the `avd_pool_role` custom field set:

| Pool | Example Prefix | `avd_pool_role` | Used For |
|------|---------------|-----------------|----------|
| Loopback | `10.255.0.0/27` | `loopback` | Router IDs (Loopback0) for spines and leafs |
| VTEP | `10.255.1.0/27` | `vtep` | VXLAN tunnel source (Loopback1) on leafs |
| P2P Uplinks | `10.255.255.0/26` | `p2p_uplink` | Point-to-point links between spines and leafs |
| MLAG Peer | `10.255.1.64/27` | `mlag_peer` | MLAG peer-link (VLAN 4094) |
| MLAG Peer L3 | `10.255.1.96/27` | `mlag_peer_l3` | iBGP peering between MLAG peers (VLAN 4093) |

## VLANs and Network Services

VLANs are automatically classified as either **SVIs** (routed) or **L2 VLANs** (bridged):

- A VLAN with a **prefix** assigned to it in a **VRF** becomes an SVI with `ip_address_virtual` derived from the prefix (`.1` gateway)
- A VLAN **without** a prefix or VRF becomes a pure L2 VLAN

```
VLAN 11 (VRF10_VLAN11)
  └── Prefix 10.10.11.0/24 (VRF: VRF10)
      └── Generates: SVI with ip_address_virtual: 10.10.11.1/24

VLAN 3401 (L2_VLAN3401)
  └── No prefix
      └── Generates: L2 VLAN (bridged in VXLAN)
```

!!! note "Tenant assignment"
    VLANs **must** have a tenant assigned in NetBox to appear in network services. VLANs without a tenant are skipped (e.g., native VLANs used only for trunk ports).

## Connected Endpoints (Cables)

Server-to-switch connections are discovered automatically from NetBox cables:

1. Create a **device** with role `server`
2. Create **interfaces** on both the server and the leaf switch
3. Create a **cable** connecting them
4. On the **switch interface**, set:
    - **Mode**: `access` or `tagged`
    - **Untagged VLAN**: for access ports or trunk native VLAN
    - **Tagged VLANs**: for trunk ports
5. For **port-channels**: create a LAG interface on the switch and assign the physical interface as a member

The collection detects LAG membership and multi-switch cables to automatically generate port-channel configurations.

## Example: Single-DC L3LS

Here's the complete NetBox setup for the reference topology:

```
Site: DC1
├── Spines (role=spine, bgp_as=65100)
│   ├── dc1-spine1 (node_id=1, mgmt=172.16.1.11/24)
│   └── dc1-spine2 (node_id=2, mgmt=172.16.1.12/24)
├── L3 Leafs (role=l3-leaf)
│   ├── dc1-leaf1a (node_id=1, group=DC1_L3_LEAF1, bgp_as=65101)
│   ├── dc1-leaf1b (node_id=2, group=DC1_L3_LEAF1, bgp_as=65101)
│   ├── dc1-leaf2a (node_id=3, group=DC1_L3_LEAF2, bgp_as=65102)
│   └── dc1-leaf2b (node_id=4, group=DC1_L3_LEAF2, bgp_as=65102)
├── L2 Leafs (role=l2-leaf)
│   ├── dc1-leaf1c (node_id=1, group=DC1_L2_LEAF1)
│   └── dc1-leaf2c (node_id=1, group=DC1_L2_LEAF2)
├── Tenant: TENANT1 (mac_vrf_vni_base=10000)
│   ├── VRF10 (vni=10) → VLANs 11,12 with prefixes
│   └── VRF11 (vni=11) → VLANs 21,22 with prefixes
├── L2 VLANs: 3401, 3402
├── IP Pools: loopback, vtep, p2p_uplink, mlag_peer, mlag_peer_l3
└── Servers: dc1-leaf1-server1, dc1-leaf2-server1 (cabled to leafs)
```
