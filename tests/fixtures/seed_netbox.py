#!/usr/bin/env python3
"""Idempotent NetBox seeder for AVD test topologies.

Supports both single-dc-l3ls and dual-dc-l3ls topologies.
Usage:
  python seed_netbox.py              # Seeds DC1 only (single-dc)
  python seed_netbox.py --dual-dc    # Seeds DC1 + DC2 (dual-dc)
"""

import os
import sys

import pynetbox

NETBOX_URL = os.environ.get("NETBOX_URL", "http://localhost:18080")
NETBOX_TOKEN = os.environ.get(
    "NETBOX_TOKEN", "0123456789abcdef0123456789abcdef01234567"
)

SITES = {
    "dc1": {
        "name": "DC1",
        "devices": [
            {"name": "dc1-spine1", "role": "spine", "dtype": "cEOSLab-spine",
             "node_id": 1, "node_group": None, "bgp_as": 65100,
             "mgmt_ip": "172.16.1.11/24"},
            {"name": "dc1-spine2", "role": "spine", "dtype": "cEOSLab-spine",
             "node_id": 2, "node_group": None, "bgp_as": 65100,
             "mgmt_ip": "172.16.1.12/24"},
            {"name": "dc1-leaf1a", "role": "l3-leaf", "dtype": "cEOSLab-l3leaf",
             "node_id": 1, "node_group": "DC1_L3_LEAF1", "bgp_as": 65101,
             "mgmt_ip": "172.16.1.101/24"},
            {"name": "dc1-leaf1b", "role": "l3-leaf", "dtype": "cEOSLab-l3leaf",
             "node_id": 2, "node_group": "DC1_L3_LEAF1", "bgp_as": 65101,
             "mgmt_ip": "172.16.1.102/24"},
            {"name": "dc1-leaf2a", "role": "l3-leaf", "dtype": "cEOSLab-l3leaf",
             "node_id": 3, "node_group": "DC1_L3_LEAF2", "bgp_as": 65102,
             "mgmt_ip": "172.16.1.103/24"},
            {"name": "dc1-leaf2b", "role": "l3-leaf", "dtype": "cEOSLab-l3leaf",
             "node_id": 4, "node_group": "DC1_L3_LEAF2", "bgp_as": 65102,
             "mgmt_ip": "172.16.1.104/24"},
            {"name": "dc1-leaf1c", "role": "l2-leaf", "dtype": "cEOSLab-l2leaf",
             "node_id": 1, "node_group": "DC1_L2_LEAF1", "bgp_as": None,
             "mgmt_ip": "172.16.1.151/24"},
            {"name": "dc1-leaf2c", "role": "l2-leaf", "dtype": "cEOSLab-l2leaf",
             "node_id": 1, "node_group": "DC1_L2_LEAF2", "bgp_as": None,
             "mgmt_ip": "172.16.1.152/24"},
        ],
        "servers": [
            {"name": "dc1-leaf1-server1", "adapters": [
                {"endpoint_ports": ["PCI1", "PCI2"],
                 "switch_ports": ["Ethernet5", "Ethernet5"],
                 "switches": ["dc1-leaf1a", "dc1-leaf1b"],
                 "vlans": [11, 12, 21, 22], "native_vlan": 4092,
                 "mode": "tagged", "port_channel": True},
                {"endpoint_ports": ["iLO"],
                 "switch_ports": ["Ethernet5"],
                 "switches": ["dc1-leaf1c"],
                 "vlans": [11], "native_vlan": None,
                 "mode": "access", "port_channel": False},
            ]},
            {"name": "dc1-leaf2-server1", "adapters": [
                {"endpoint_ports": ["PCI1", "PCI2"],
                 "switch_ports": ["Ethernet5", "Ethernet5"],
                 "switches": ["dc1-leaf2a", "dc1-leaf2b"],
                 "vlans": [11, 12, 21, 22], "native_vlan": 4092,
                 "mode": "tagged", "port_channel": True},
                {"endpoint_ports": ["iLO"],
                 "switch_ports": ["Ethernet5"],
                 "switches": ["dc1-leaf2c"],
                 "vlans": [11], "native_vlan": None,
                 "mode": "access", "port_channel": False},
            ]},
        ],
        "pools": [
            {"prefix": "10.255.0.0/27", "role": "loopback"},
            {"prefix": "10.255.1.0/27", "role": "vtep"},
            {"prefix": "10.255.255.0/26", "role": "p2p_uplink"},
            {"prefix": "10.255.1.64/27", "role": "mlag_peer"},
            {"prefix": "10.255.1.96/27", "role": "mlag_peer_l3"},
        ],
    },
    "dc2": {
        "name": "DC2",
        "devices": [
            {"name": "dc2-spine1", "role": "spine", "dtype": "cEOSLab-spine",
             "node_id": 1, "node_group": None, "bgp_as": 65200,
             "mgmt_ip": "172.16.1.21/24"},
            {"name": "dc2-spine2", "role": "spine", "dtype": "cEOSLab-spine",
             "node_id": 2, "node_group": None, "bgp_as": 65200,
             "mgmt_ip": "172.16.1.22/24"},
            {"name": "dc2-leaf1a", "role": "l3-leaf", "dtype": "cEOSLab-l3leaf",
             "node_id": 1, "node_group": "DC2_L3_LEAF1", "bgp_as": 65201,
             "mgmt_ip": "172.16.1.111/24"},
            {"name": "dc2-leaf1b", "role": "l3-leaf", "dtype": "cEOSLab-l3leaf",
             "node_id": 2, "node_group": "DC2_L3_LEAF1", "bgp_as": 65201,
             "mgmt_ip": "172.16.1.112/24"},
            {"name": "dc2-leaf2a", "role": "l3-leaf", "dtype": "cEOSLab-l3leaf",
             "node_id": 3, "node_group": "DC2_L3_LEAF2", "bgp_as": 65202,
             "mgmt_ip": "172.16.1.113/24"},
            {"name": "dc2-leaf2b", "role": "l3-leaf", "dtype": "cEOSLab-l3leaf",
             "node_id": 4, "node_group": "DC2_L3_LEAF2", "bgp_as": 65202,
             "mgmt_ip": "172.16.1.114/24"},
            {"name": "dc2-leaf1c", "role": "l2-leaf", "dtype": "cEOSLab-l2leaf",
             "node_id": 1, "node_group": "DC2_L2_LEAF1", "bgp_as": None,
             "mgmt_ip": "172.16.1.161/24"},
            {"name": "dc2-leaf2c", "role": "l2-leaf", "dtype": "cEOSLab-l2leaf",
             "node_id": 1, "node_group": "DC2_L2_LEAF2", "bgp_as": None,
             "mgmt_ip": "172.16.1.162/24"},
        ],
        "servers": [
            {"name": "dc2-leaf1-server1", "adapters": [
                {"endpoint_ports": ["PCI1", "PCI2"],
                 "switch_ports": ["Ethernet5", "Ethernet5"],
                 "switches": ["dc2-leaf1a", "dc2-leaf1b"],
                 "vlans": [11, 12, 21, 22], "native_vlan": 4092,
                 "mode": "tagged", "port_channel": True},
                {"endpoint_ports": ["iLO"],
                 "switch_ports": ["Ethernet5"],
                 "switches": ["dc2-leaf1c"],
                 "vlans": [11], "native_vlan": None,
                 "mode": "access", "port_channel": False},
            ]},
            {"name": "dc2-leaf2-server1", "adapters": [
                {"endpoint_ports": ["PCI1", "PCI2"],
                 "switch_ports": ["Ethernet5", "Ethernet5"],
                 "switches": ["dc2-leaf2a", "dc2-leaf2b"],
                 "vlans": [11, 12, 21, 22], "native_vlan": 4092,
                 "mode": "tagged", "port_channel": True},
                {"endpoint_ports": ["iLO"],
                 "switch_ports": ["Ethernet5"],
                 "switches": ["dc2-leaf2c"],
                 "vlans": [11], "native_vlan": None,
                 "mode": "access", "port_channel": False},
            ]},
        ],
        "pools": [
            {"prefix": "10.255.128.0/27", "role": "loopback"},
            {"prefix": "10.255.129.0/27", "role": "vtep"},
            {"prefix": "10.255.255.64/26", "role": "p2p_uplink"},
            {"prefix": "10.255.129.64/27", "role": "mlag_peer"},
            {"prefix": "10.255.129.96/27", "role": "mlag_peer_l3"},
        ],
    },
}

VRFS = [
    {"name": "VRF10", "vrf_vni": 10, "vtep_diag_loopback": 10,
     "vtep_diag_ip_range": "10.255.10.0/27"},
    {"name": "VRF11", "vrf_vni": 11, "vtep_diag_loopback": 11,
     "vtep_diag_ip_range": "10.255.11.0/27"},
]

VLANS = [
    {"vid": 11, "name": "VRF10_VLAN11", "vrf": "VRF10",
     "prefix": "10.10.11.0/24"},
    {"vid": 12, "name": "VRF10_VLAN12", "vrf": "VRF10",
     "prefix": "10.10.12.0/24"},
    {"vid": 21, "name": "VRF11_VLAN21", "vrf": "VRF11",
     "prefix": "10.10.21.0/24"},
    {"vid": 22, "name": "VRF11_VLAN22", "vrf": "VRF11",
     "prefix": "10.10.22.0/24"},
    {"vid": 3401, "name": "L2_VLAN3401", "vrf": None, "prefix": None},
    {"vid": 3402, "name": "L2_VLAN3402", "vrf": None, "prefix": None},
]

# DCI cables between border leafs (dual-dc only)
DCI_CABLES = [
    {"a_device": "dc1-leaf2a", "a_port": "Ethernet6",
     "b_device": "dc2-leaf2a", "b_port": "Ethernet6"},
    {"a_device": "dc1-leaf2b", "a_port": "Ethernet6",
     "b_device": "dc2-leaf2b", "b_port": "Ethernet6"},
]


def get_or_create(endpoint, search_params, create_params=None):
    existing = list(endpoint.filter(**search_params))
    if existing:
        return existing[0]
    params = {**search_params, **(create_params or {})}
    return endpoint.create(params)


def create_cable(nb, dev_objs, a_dev, a_port, b_dev, b_port):
    """Create interface + cable between two devices."""
    a = dev_objs[a_dev]
    b = dev_objs[b_dev]
    a_iface = get_or_create(
        nb.dcim.interfaces, {"device_id": a.id, "name": a_port},
        {"device": a.id, "name": a_port, "type": "1000base-t"})
    b_iface = get_or_create(
        nb.dcim.interfaces, {"device_id": b.id, "name": b_port},
        {"device": b.id, "name": b_port, "type": "1000base-t"})

    for c in nb.dcim.cables.filter(device_id=[a.id]):
        terms = list(c.a_terminations or []) + list(c.b_terminations or [])
        for t in terms:
            obj = t.get("object", {}) if isinstance(t, dict) else getattr(t, "object", {})
            obj_id = obj.get("id") if isinstance(obj, dict) else getattr(obj, "id", None)
            if obj_id == a_iface.id:
                return
    try:
        nb.dcim.cables.create({
            "a_terminations": [{"object_type": "dcim.interface",
                                "object_id": a_iface.id}],
            "b_terminations": [{"object_type": "dcim.interface",
                                "object_id": b_iface.id}],
            "status": "connected"})
    except Exception as e:
        print(f"    Cable {a_dev}/{a_port}->{b_dev}/{b_port}: {e}")


def seed(site_slugs=None):
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
    if site_slugs is None:
        site_slugs = ["dc1"]

    # --- Custom fields ---
    print("Creating custom fields...")
    cf_defs = [
        {"name": "avd_node_id", "type": "integer", "label": "AVD Node ID",
         "object_types": ["dcim.device"]},
        {"name": "avd_node_group", "type": "text", "label": "AVD Node Group",
         "object_types": ["dcim.device"]},
        {"name": "avd_bgp_as", "type": "integer", "label": "AVD BGP AS",
         "object_types": ["dcim.device"]},
        {"name": "avd_vrf_vni", "type": "integer", "label": "AVD VRF VNI",
         "object_types": ["ipam.vrf"]},
        {"name": "avd_vtep_diagnostic_loopback", "type": "integer",
         "label": "AVD VTEP Diag Loopback", "object_types": ["ipam.vrf"]},
        {"name": "avd_vtep_diagnostic_loopback_ip_range", "type": "text",
         "label": "AVD VTEP Diag IP Range", "object_types": ["ipam.vrf"]},
        {"name": "avd_mac_vrf_vni_base", "type": "integer",
         "label": "AVD MAC VRF VNI Base",
         "object_types": ["tenancy.tenant"]},
        {"name": "avd_pool_role", "type": "text",
         "label": "AVD Pool Role", "object_types": ["ipam.prefix"]},
    ]
    for cf in cf_defs:
        if not list(nb.extras.custom_fields.filter(name=cf["name"])):
            nb.extras.custom_fields.create(cf)
            print(f"  Created: {cf['name']}")
        else:
            print(f"  Exists: {cf['name']}")

    # --- Infrastructure (shared) ---
    print("Creating shared infrastructure...")
    region = get_or_create(nb.dcim.regions, {"slug": "us-east"},
                           {"name": "US-East"})
    mfr = get_or_create(nb.dcim.manufacturers, {"slug": "arista"},
                         {"name": "Arista"})
    roles = {}
    for rd in [{"name": "Spine", "slug": "spine", "color": "aa1409"},
               {"name": "L3 Leaf", "slug": "l3-leaf", "color": "2196f3"},
               {"name": "L2 Leaf", "slug": "l2-leaf", "color": "4caf50"},
               {"name": "Server", "slug": "server", "color": "9e9e9e"}]:
        roles[rd["slug"]] = get_or_create(nb.dcim.device_roles,
                                           {"slug": rd["slug"]}, rd)
    dtypes = {}
    for d in [{"model": "cEOSLab-spine", "slug": "ceoslab-spine"},
              {"model": "cEOSLab-l3leaf", "slug": "ceoslab-l3leaf"},
              {"model": "cEOSLab-l2leaf", "slug": "ceoslab-l2leaf"},
              {"model": "Generic Server", "slug": "generic-server"}]:
        dtypes[d["model"]] = get_or_create(
            nb.dcim.device_types, {"slug": d["slug"]},
            {**d, "manufacturer": mfr.id})

    # --- Tenant + VRFs (shared) ---
    print("Creating tenant and VRFs...")
    tenant = get_or_create(nb.tenancy.tenants, {"slug": "tenant1"},
                            {"name": "TENANT1",
                             "custom_fields": {"avd_mac_vrf_vni_base": 10000}})
    if tenant.custom_fields.get("avd_mac_vrf_vni_base") != 10000:
        tenant.custom_fields = {"avd_mac_vrf_vni_base": 10000}
        tenant.save()

    vrf_objs = {}
    for vd in VRFS:
        cf = {"avd_vrf_vni": vd["vrf_vni"],
              "avd_vtep_diagnostic_loopback": vd["vtep_diag_loopback"],
              "avd_vtep_diagnostic_loopback_ip_range": vd["vtep_diag_ip_range"]}
        vrf = get_or_create(nb.ipam.vrfs, {"name": vd["name"]},
                             {"name": vd["name"], "tenant": tenant.id,
                              "custom_fields": cf})
        if (vrf.custom_fields or {}).get("avd_vrf_vni") != vd["vrf_vni"]:
            vrf.custom_fields = cf
            vrf.save()
        vrf_objs[vd["name"]] = vrf
        print(f"  {vd['name']} (vni={vd['vrf_vni']})")

    dev_objs = {}
    total_devs = 0
    total_srvs = 0

    for site_slug in site_slugs:
        site_data = SITES[site_slug]
        print(f"\n=== Site: {site_data['name']} ===")

        site = get_or_create(nb.dcim.sites, {"slug": site_slug},
                              {"name": site_data["name"], "region": region.id,
                               "status": "active"})

        # --- VLANs + prefixes (per-site) ---
        print("  VLANs and prefixes...")
        vlan_objs = {}
        for vd in VLANS:
            vlan = get_or_create(
                nb.ipam.vlans, {"vid": vd["vid"], "site_id": site.id},
                {"vid": vd["vid"], "name": vd["name"], "site": site.id,
                 "tenant": tenant.id, "status": "active"})
            vlan_objs[vd["vid"]] = vlan
            if vd["prefix"]:
                vrf_id = vrf_objs[vd["vrf"]].id if vd["vrf"] else None
                existing = list(nb.ipam.prefixes.filter(
                    prefix=vd["prefix"], vrf_id=vrf_id))
                if not existing:
                    nb.ipam.prefixes.create(
                        {"prefix": vd["prefix"], "site": site.id,
                         "vlan": vlan.id, "vrf": vrf_id,
                         "tenant": tenant.id, "status": "active"})

        # --- IP pools (per-site) ---
        print("  IP pools...")
        for pool in site_data["pools"]:
            pfx = get_or_create(
                nb.ipam.prefixes,
                {"prefix": pool["prefix"], "site_id": site.id,
                 "cf_avd_pool_role": pool["role"]},
                {"prefix": pool["prefix"], "site": site.id,
                 "status": "active",
                 "custom_fields": {"avd_pool_role": pool["role"]}})
            if (pfx.custom_fields or {}).get("avd_pool_role") != pool["role"]:
                pfx.custom_fields = {"avd_pool_role": pool["role"]}
                pfx.save()
            print(f"    {pool['prefix']} -> {pool['role']}")

        # --- Network devices ---
        print("  Devices...")
        for dd in site_data["devices"]:
            cf = {"avd_node_id": dd["node_id"],
                  "avd_node_group": dd["node_group"],
                  "avd_bgp_as": dd["bgp_as"]}
            dev = get_or_create(
                nb.dcim.devices, {"name": dd["name"]},
                {"name": dd["name"], "role": roles[dd["role"]].id,
                 "device_type": dtypes[dd["dtype"]].id,
                 "site": site.id, "status": "active",
                 "custom_fields": cf})
            dcf = dev.custom_fields or {}
            if (dcf.get("avd_node_id") != dd["node_id"]
                    or dcf.get("avd_bgp_as") != dd["bgp_as"]
                    or dcf.get("avd_node_group") != dd["node_group"]):
                dev.custom_fields = cf
                dev.save()
            mgmt = get_or_create(
                nb.dcim.interfaces,
                {"device_id": dev.id, "name": "Management0"},
                {"device": dev.id, "name": "Management0", "type": "virtual"})
            ips = list(nb.ipam.ip_addresses.filter(
                address=dd["mgmt_ip"], interface_id=mgmt.id))
            ip = ips[0] if ips else nb.ipam.ip_addresses.create(
                {"address": dd["mgmt_ip"],
                 "assigned_object_type": "dcim.interface",
                 "assigned_object_id": mgmt.id})
            if not dev.primary_ip4 or dev.primary_ip4.id != ip.id:
                dev.primary_ip4 = ip.id
                dev.save()
            dev_objs[dd["name"]] = dev
            print(f"    {dd['name']}: AS={dd['bgp_as']}, "
                  f"group={dd['node_group']}")
            total_devs += 1

        # --- Servers + cables ---
        print("  Servers and cabling...")
        for srv in site_data["servers"]:
            server = get_or_create(
                nb.dcim.devices, {"name": srv["name"]},
                {"name": srv["name"], "role": roles["server"].id,
                 "device_type": dtypes["Generic Server"].id,
                 "site": site.id, "status": "active"})
            dev_objs[srv["name"]] = server

            for adapter in srv["adapters"]:
                for ep_port, sw_port, sw_name in zip(
                        adapter["endpoint_ports"],
                        adapter["switch_ports"],
                        adapter["switches"]):
                    get_or_create(
                        nb.dcim.interfaces,
                        {"device_id": server.id, "name": ep_port},
                        {"device": server.id, "name": ep_port,
                         "type": "1000base-t"})
                    switch = dev_objs[sw_name]
                    sw_iface = get_or_create(
                        nb.dcim.interfaces,
                        {"device_id": switch.id, "name": sw_port},
                        {"device": switch.id, "name": sw_port,
                         "type": "1000base-t"})
                    sw_iface.mode = adapter["mode"]
                    if adapter["mode"] == "access" and adapter["vlans"]:
                        vid = adapter["vlans"][0]
                        if vid in vlan_objs:
                            sw_iface.untagged_vlan = vlan_objs[vid].id
                    elif adapter["mode"] == "tagged":
                        tagged = [vlan_objs[v].id for v in adapter["vlans"]
                                  if v in vlan_objs]
                        sw_iface.tagged_vlans = tagged
                        if adapter.get("native_vlan"):
                            nv = get_or_create(
                                nb.ipam.vlans,
                                {"vid": adapter["native_vlan"],
                                 "site_id": site.id},
                                {"vid": adapter["native_vlan"],
                                 "name": f"NATIVE_{adapter['native_vlan']}",
                                 "site": site.id, "status": "active"})
                            sw_iface.untagged_vlan = nv.id
                    sw_iface.save()
                    create_cable(nb, dev_objs, srv["name"], ep_port,
                                 sw_name, sw_port)

                if adapter["port_channel"] and len(adapter["switches"]) > 1:
                    for sw_name, sw_port in zip(adapter["switches"],
                                                 adapter["switch_ports"]):
                        switch = dev_objs[sw_name]
                        lag_name = f"Port-Channel{sw_port.replace('Ethernet', '')}"
                        lag = get_or_create(
                            nb.dcim.interfaces,
                            {"device_id": switch.id, "name": lag_name},
                            {"device": switch.id, "name": lag_name,
                             "type": "lag"})
                        members = list(nb.dcim.interfaces.filter(
                            device_id=switch.id, name=sw_port))
                        if members and not members[0].lag:
                            members[0].lag = lag.id
                            members[0].save()

            print(f"    {srv['name']}: {len(srv['adapters'])} adapters")
            total_srvs += 1

    # --- DCI cables (dual-dc only) ---
    if len(site_slugs) > 1:
        print("\nCreating DCI cables...")
        for dci in DCI_CABLES:
            create_cable(nb, dev_objs,
                         dci["a_device"], dci["a_port"],
                         dci["b_device"], dci["b_port"])
            print(f"  {dci['a_device']}/{dci['a_port']} <-> "
                  f"{dci['b_device']}/{dci['b_port']}")

    print("\nSeeding complete!")
    print(f"  Sites: {', '.join(site_slugs)}")
    print(f"  Network devices: {total_devs}")
    print(f"  Servers: {total_srvs}")
    print(f"  VLANs: {len(VLANS)}, VRFs: {len(VRFS)}, Tenant: TENANT1")


if __name__ == "__main__":
    dual = "--dual-dc" in sys.argv
    try:
        if dual:
            seed(["dc1", "dc2"])
        else:
            seed(["dc1"])
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
