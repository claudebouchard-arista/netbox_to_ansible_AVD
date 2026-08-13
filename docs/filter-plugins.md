# Filter Plugins

The collection provides Jinja2 filter plugins that transform NetBox API data into AVD-compatible structures. These are used internally by the `generate_avd` role but can also be used directly in custom playbooks.

## Filters

### `to_avd_inventory`

Builds the AVD `inventory.yml` structure from NetBox devices.

```yaml
{{ devices | arista.netbox_avd.to_avd_inventory(site_name, role_mapping, ip_addresses, mgmt_interface_name) }}
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `devices` | list | NetBox device dicts |
| `site_name` | string | Site slug (e.g., `dc1` → groups named `DC1_SPINES`, etc.) |
| `role_mapping` | dict | Maps NetBox role slugs to AVD types (`{spine: spine, l3-leaf: l3leaf, ...}`) |
| `ip_addresses` | list | NetBox IP address dicts for management IPs |
| `mgmt_interface_name` | string | Management interface name (default: `Management0`) |

**Output:** Dict with `all.children.FABRIC`, `NETWORK_SERVICES`, `CONNECTED_ENDPOINTS` groups.

---

### `to_avd_spine_nodes`

Converts spine devices to AVD node list.

```yaml
{{ spine_devices | arista.netbox_avd.to_avd_spine_nodes(ip_addresses, node_id_field, mgmt_interface_name) }}
```

**Output:** `[{name: dc1-spine1, id: 1, mgmt_ip: 172.16.1.11/24}, ...]`

---

### `to_avd_spine_names`

Extracts sorted spine names for `uplink_switches`.

```yaml
{{ spine_devices | arista.netbox_avd.to_avd_spine_names }}
```

**Output:** `['dc1-spine1', 'dc1-spine2']`

---

### `to_avd_spine_bgp_as`

Extracts BGP AS from spine devices.

```yaml
{{ spine_devices | arista.netbox_avd.to_avd_spine_bgp_as }}
```

**Output:** `65100`

---

### `to_avd_l3leaf_node_groups`

Builds L3 leaf node groups by merging NetBox devices into defaults. Groups devices by `avd_node_group` custom field. Injects BGP AS from `avd_bgp_as` custom field.

```yaml
{{ l3leaf_devices | arista.netbox_avd.to_avd_l3leaf_node_groups(defaults, ip_addresses, node_id_field, node_group_field, mgmt_interface_name) }}
```

**Output:**
```yaml
- group: DC1_L3_LEAF1
  bgp_as: 65101
  nodes:
    - name: dc1-leaf1a
      id: 1
      mgmt_ip: 172.16.1.101/24
    - name: dc1-leaf1b
      id: 2
      mgmt_ip: 172.16.1.102/24
```

---

### `to_avd_l2leaf_node_groups`

Same as `to_avd_l3leaf_node_groups` but for L2 leaf devices.

---

### `to_avd_network_services`

Builds AVD `tenants` structure from NetBox VLANs, VRFs, prefixes, and tenants.

```yaml
{{ vlans | arista.netbox_avd.to_avd_network_services(vrfs, prefixes, tenants, defaults) }}
```

**Logic:**

- Groups VLANs by tenant
- VLANs with a prefix in a VRF become SVIs with `ip_address_virtual` (derived as `.1` of the prefix)
- VLANs without a prefix/VRF become L2 VLANs
- VRF custom fields provide `vrf_vni` and `vtep_diagnostic`
- Tenant custom field provides `mac_vrf_vni_base`
- VLANs without a tenant are skipped

---

### `to_avd_connected_endpoints`

Builds AVD `servers` structure from NetBox cables, interfaces, and devices.

```yaml
{{ cables | arista.netbox_avd.to_avd_connected_endpoints(interfaces, devices, role_mapping) }}
```

**Logic:**

- Finds cables between network devices (spine/leaf) and non-network devices (servers)
- Reads interface mode, tagged/untagged VLANs, and LAG membership from switch ports
- Generates port-channel config for multi-switch LAG adapters
- Formats VLAN lists as compact ranges (`11-12,21-22`)

---

### `to_avd_ip_pools`

Extracts AVD IP pools from NetBox prefixes tagged with `avd_pool_role`.

```yaml
{{ prefixes | arista.netbox_avd.to_avd_ip_pools }}
```

**Output:**
```yaml
loopback: 10.255.0.0/27
vtep: 10.255.1.0/27
p2p_uplink: 10.255.255.0/26
mlag_peer: 10.255.1.64/27
mlag_peer_l3: 10.255.1.96/27
```

---

### `to_avd_merge_defaults`

Deep-merges two dicts (NetBox data on top of local defaults).

```yaml
{{ base_dict | arista.netbox_avd.to_avd_merge_defaults(override_dict) }}
```

Recursive merge: nested dicts are merged key-by-key. Non-dict values in override replace the base.
