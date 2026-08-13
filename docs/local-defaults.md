# Local Defaults

The `avd_defaults/` directory contains YAML files with AVD-specific settings that don't belong in NetBox. These are merged with NetBox data to produce the final AVD inventory.

## File Reference

### `fabric.yml`

Global fabric settings applied to all devices.

```yaml
fabric_name: FABRIC
underlay_routing_protocol: ebgp
overlay_routing_protocol: ebgp

aaa_settings:
  local_users:
    - name: admin
      privilege: 15
      role: network-admin
      no_password: true

bgp_peer_groups:
  evpn_overlay_peers:
    password: <encrypted>
  ipv4_underlay_peers:
    password: <encrypted>
  mlag_ipv4_underlay_peer:
    password: <encrypted>

default_interfaces:
  - types: [spine]
    platforms: [default]
    uplink_interfaces: [Ethernet1-2]
    downlink_interfaces: [Ethernet1-8]
  - types: [l3leaf]
    platforms: [default]
    uplink_interfaces: [Ethernet1-2]
    mlag_interfaces: [Ethernet3-4]
    downlink_interfaces: [Ethernet8]
  - types: [l2leaf]
    platforms: [default]
    uplink_interfaces: [Ethernet1-2]

dns_settings:
  servers:
    - ip_address: 192.168.1.1

ntp_settings:
  server_vrf: use_mgmt_interface_vrf
  servers:
    - name: 0.pool.ntp.org
```

### `connectivity.yml`

Ansible connection settings for reaching the devices.

```yaml
ansible_connection: ansible.netcommon.httpapi
ansible_network_os: arista.eos.eos
ansible_user: arista
ansible_password: arista
ansible_become: true
ansible_become_method: enable
ansible_httpapi_use_ssl: true
ansible_httpapi_validate_certs: false
```

### `dc.yml`

Per-DC settings (management gateway, eAPI).

```yaml
mgmt_gateway: 172.16.1.1
management_eapi:
  enabled: true
```

### `spines.yml`

Spine-specific defaults. BGP AS and loopback pool come from NetBox.

```yaml
spine:
  defaults:
    platform: cEOSLab
```

### `l3_leaves.yml`

L3 leaf defaults. IP pools, BGP AS, uplink_switches, and nodes all come from NetBox.

```yaml
l3leaf:
  defaults:
    platform: cEOSLab
    loopback_ipv4_offset: 2
    virtual_router_mac_address: 00:1c:73:00:00:99
    spanning_tree_priority: 4096
    spanning_tree_mode: mstp
```

### `l2_leaves.yml`

L2 leaf defaults. Node groups and uplink_switches are defined here (uplink_switches could come from NetBox cables in a future version).

```yaml
l2leaf:
  defaults:
    platform: cEOSLab
    spanning_tree_mode: mstp
  node_groups:
    - group: DC1_L2_LEAF1
      uplink_switches: [dc1-leaf1a, dc1-leaf1b]
    - group: DC1_L2_LEAF2
      uplink_switches: [dc1-leaf2a, dc1-leaf2b]
```

### `network_services.yml`

Can be empty -- network services are auto-generated from NetBox VLANs, VRFs, and prefixes. Use this file to add overrides that get deep-merged on top.

### `connected_endpoints.yml`

Can be empty -- connected endpoints are auto-generated from NetBox cables and interface configurations. Use this file for overrides.

## What's In NetBox vs Local Defaults

!!! question "Why not put everything in NetBox?"
    Some settings are genuinely AVD-specific and would pollute NetBox without adding value as a network source of truth. Passwords and secrets should never be in NetBox. Interface naming patterns are platform-specific, not topology data.

| Setting | In NetBox? | Why |
|---------|-----------|-----|
| Device names, roles, IPs | Yes | Core topology data |
| BGP AS numbers | Yes | Routing intent |
| IP pools | Yes | IPAM data |
| VLANs, VRFs, tenants | Yes | Network services |
| Server connections | Yes | Physical cabling |
| Platform type | Local | AVD platform string, not NetBox device type |
| Spanning tree settings | Local | AVD design parameter |
| BGP peer-group passwords | Local | Secrets don't belong in NetBox |
| AAA users/passwords | Local | Secrets |
| DNS/NTP servers | Local | Infrastructure services |
| Interface naming patterns | Local | Platform-specific convention |
| Virtual router MAC | Local | AVD EVPN parameter |
| Ansible connectivity | Local | Ansible-specific, not network data |
