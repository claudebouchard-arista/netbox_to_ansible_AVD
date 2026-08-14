# L2LS_SITE1

## Table of Contents

- [Fabric Switches and Management IP](#fabric-switches-and-management-ip)
  - [Fabric Switches with inband Management IP](#fabric-switches-with-inband-management-ip)
- [Fabric Topology](#fabric-topology)
- [Fabric IP Allocation](#fabric-ip-allocation)
  - [Fabric Point-To-Point Links](#fabric-point-to-point-links)
  - [Point-To-Point Links Node Allocation](#point-to-point-links-node-allocation)
  - [Loopback Interfaces (BGP EVPN Peering)](#loopback-interfaces-bgp-evpn-peering)
  - [Loopback0 Interfaces Node Allocation](#loopback0-interfaces-node-allocation)
  - [VTEP Loopback VXLAN Tunnel Source Interfaces (VTEPs Only)](#vtep-loopback-vxlan-tunnel-source-interfaces-vteps-only)
  - [VTEP Loopback Node allocation](#vtep-loopback-node-allocation)
- [Connected Endpoints](#connected-endpoints)
  - [Connected Endpoint Keys](#connected-endpoint-keys)
  - [Servers](#servers)

## Fabric Switches and Management IP

| POD | Type | Node | Management IP | Platform | Provisioned in CloudVision | Serial Number |
| --- | ---- | ---- | ------------- | -------- | -------------------------- | ------------- |
| L2LS_SITE1 | l2leaf | l2ls-leaf1 | 172.16.100.105/24 | cEOSLab | Provisioned | - |
| L2LS_SITE1 | l2leaf | l2ls-leaf2 | 172.16.100.106/24 | cEOSLab | Provisioned | - |
| L2LS_SITE1 | l2leaf | l2ls-leaf3 | 172.16.100.107/24 | cEOSLab | Provisioned | - |
| L2LS_SITE1 | l2leaf | l2ls-leaf4 | 172.16.100.108/24 | cEOSLab | Provisioned | - |
| L2LS_SITE1 | l2spine | l2ls-spine1 | 172.16.100.101/24 | cEOSLab | Provisioned | - |
| L2LS_SITE1 | l2spine | l2ls-spine2 | 172.16.100.102/24 | cEOSLab | Provisioned | - |

> Provision status is based on Ansible inventory declaration and do not represent real status from CloudVision.

### Fabric Switches with inband Management IP

| POD | Type | Node | Management IP | Inband Interface |
| --- | ---- | ---- | ------------- | ---------------- |

## Fabric Topology

| Type | Node | Node Interface | Peer Type | Peer Node | Peer Interface |
| ---- | ---- | -------------- | --------- | --------- | -------------- |
| l2leaf | l2ls-leaf1 | Ethernet1 | l2spine | l2ls-spine1 | Ethernet1 |
| l2leaf | l2ls-leaf1 | Ethernet2 | l2spine | l2ls-spine2 | Ethernet1 |
| l2leaf | l2ls-leaf1 | Ethernet47 | mlag_peer | l2ls-leaf2 | Ethernet47 |
| l2leaf | l2ls-leaf1 | Ethernet48 | mlag_peer | l2ls-leaf2 | Ethernet48 |
| l2leaf | l2ls-leaf2 | Ethernet1 | l2spine | l2ls-spine1 | Ethernet2 |
| l2leaf | l2ls-leaf2 | Ethernet2 | l2spine | l2ls-spine2 | Ethernet2 |
| l2leaf | l2ls-leaf3 | Ethernet1 | l2spine | l2ls-spine1 | Ethernet3 |
| l2leaf | l2ls-leaf3 | Ethernet2 | l2spine | l2ls-spine2 | Ethernet3 |
| l2leaf | l2ls-leaf3 | Ethernet47 | mlag_peer | l2ls-leaf4 | Ethernet47 |
| l2leaf | l2ls-leaf3 | Ethernet48 | mlag_peer | l2ls-leaf4 | Ethernet48 |
| l2leaf | l2ls-leaf4 | Ethernet1 | l2spine | l2ls-spine1 | Ethernet4 |
| l2leaf | l2ls-leaf4 | Ethernet2 | l2spine | l2ls-spine2 | Ethernet4 |
| l2spine | l2ls-spine1 | Ethernet47 | mlag_peer | l2ls-spine2 | Ethernet47 |
| l2spine | l2ls-spine1 | Ethernet48 | mlag_peer | l2ls-spine2 | Ethernet48 |

## Fabric IP Allocation

### Fabric Point-To-Point Links

| Uplink IPv4 Pool | Available Addresses | Assigned addresses | Assigned Address % |
| ---------------- | ------------------- | ------------------ | ------------------ |

### Point-To-Point Links Node Allocation

| Node | Node Interface | Node IP Address | Peer Node | Peer Interface | Peer IP Address |
| ---- | -------------- | --------------- | --------- | -------------- | --------------- |

### Loopback Interfaces (BGP EVPN Peering)

| Loopback Pool | Available Addresses | Assigned addresses | Assigned Address % |
| ------------- | ------------------- | ------------------ | ------------------ |

### Loopback0 Interfaces Node Allocation

| POD | Node | Loopback0 |
| --- | ---- | --------- |

### VTEP Loopback VXLAN Tunnel Source Interfaces (VTEPs Only)

| VTEP Loopback Pool | Available Addresses | Assigned addresses | Assigned Address % |
| ------------------ | ------------------- | ------------------ | ------------------ |

### VTEP Loopback Node allocation

| POD | Node | Loopback1 |
| --- | ---- | --------- |

## Connected Endpoints

### Connected Endpoint Keys

| Key | Default Type | Description |
| --- | ------------ | ----------- |
| servers | server | Server |

### Servers

| Name | Type | Port | Fabric Device | Fabric Port | Description | Shutdown | Mode | Access VLAN | Trunk Allowed VLANs | Profile |
| ---- | ---- | ---- | ------------- | ----------- | ----------- | -------- | ---- | ----------- | ------------------- | ------- |
| l2ls-firewall | server | Eth1 | l2ls-spine1 | Port-Channel5(Ethernet5) | SERVER_l2ls-firewall | False | trunk | - | 10,20,30 | - |
| l2ls-firewall | server | Eth2 | l2ls-spine2 | Port-Channel5(Ethernet5) | SERVER_l2ls-firewall | False | trunk | - | 10,20,30 | - |
| l2ls-host2 | server | Eth1 | l2ls-leaf4 | Ethernet3 | SERVER_l2ls-host2_Eth1 | False | access | 30 | - | - |
| l2ls-hostA | server | Eth1 | l2ls-leaf1 | Ethernet3 | SERVER_l2ls-hostA_Eth1 | False | access | 10 | - | - |
| l2ls-hostB | server | Eth1 | l2ls-leaf2 | Ethernet3 | SERVER_l2ls-hostB_Eth1 | False | access | 20 | - | - |
| l2ls-hostC | server | Eth1 | l2ls-leaf3 | Ethernet3 | SERVER_l2ls-hostC_Eth1 | False | access | 10 | - | - |
