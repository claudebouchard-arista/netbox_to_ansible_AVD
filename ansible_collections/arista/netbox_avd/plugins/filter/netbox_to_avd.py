from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy


def _extract_name(obj):
    """Extract name from a NetBox object (dict or string)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("name") or obj.get("display") or str(obj)
    return str(obj)


def _extract_slug(obj):
    """Extract slug from a NetBox object (dict or string)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("slug") or obj.get("value") or obj.get("name")
    return str(obj)


def _extract_value(obj):
    """Extract value from a NetBox choice field (dict or string)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("value") or obj.get("label") or obj.get("name")
    return str(obj)


def _get_mgmt_ip(device, ip_addresses, mgmt_interface_name="Management0"):
    """Get the management IP for a device from its IP addresses.

    Looks for an IP assigned to the management interface. Falls back to
    the device's primary_ip4 if available.
    """
    device_id = device.get("id")
    for ip in ip_addresses:
        iface = ip.get("assigned_object")
        if iface and isinstance(iface, dict):
            if (
                iface.get("device", {}).get("id") == device_id
                and _extract_name(iface) == mgmt_interface_name
            ):
                return ip.get("address")

    primary = device.get("primary_ip4")
    if primary and isinstance(primary, dict):
        return primary.get("address")
    return None


def _deep_merge(base, override):
    """Recursively merge override into base. Returns a new dict."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _group_devices_by_role(devices, role_mapping):
    """Group devices by their AVD type using the role mapping."""
    grouped = {}
    for device in devices:
        role_slug = _extract_slug(device.get("role"))
        if role_slug and role_slug in role_mapping:
            avd_type = role_mapping[role_slug]
            grouped.setdefault(avd_type, []).append(device)
    return grouped


DEFAULT_GROUP_CONFIG = {
    "spine": {"suffix": "SPINES", "in_network_services": False,
              "in_connected_endpoints": False},
    "l3leaf": {"suffix": "L3_LEAVES", "in_network_services": True,
               "in_connected_endpoints": True},
    "l2leaf": {"suffix": "L2_LEAVES", "in_network_services": True,
               "in_connected_endpoints": True},
    "l2spine": {"suffix": "SPINES", "in_network_services": True,
                "in_connected_endpoints": True},
}

L2LS_GROUP_CONFIG = {
    "l2spine": {"suffix": "SPINES", "in_network_services": True,
                "in_connected_endpoints": True},
    "l2leaf": {"suffix": "LEAFS", "in_network_services": True,
               "in_connected_endpoints": True},
}


def to_avd_inventory(devices, site_name, role_mapping, ip_addresses=None,
                     mgmt_interface_name="Management0",
                     group_config=None,
                     network_services_name="NETWORK_SERVICES",
                     connected_endpoints_name="CONNECTED_ENDPOINTS"):
    """Build AVD inventory.yml structure from NetBox devices.

    Args:
        devices: List of NetBox device dicts.
        site_name: Site name used for DC group naming.
        role_mapping: Dict mapping NetBox role slugs to AVD types.
        ip_addresses: Optional IP address dicts for management IPs.
        mgmt_interface_name: Management interface name.
        group_config: Dict mapping AVD types to group naming config.
        network_services_name: Name of the network services group.
        connected_endpoints_name: Name of the connected endpoints group.
    """
    if not devices:
        return {}

    ip_addresses = ip_addresses or []
    gc = group_config or DEFAULT_GROUP_CONFIG
    dc_name = site_name.upper().replace("-", "_")
    grouped = _group_devices_by_role(devices, role_mapping)

    dc_children = {}
    ns_children = {}
    ce_children = {}

    for avd_type, devs in grouped.items():
        type_cfg = gc.get(avd_type)
        if not type_cfg:
            continue
        group_name = f"{dc_name}_{type_cfg['suffix']}"
        hosts = {}
        for dev in sorted(devs, key=lambda d: d.get("name", "")):
            name = dev.get("name")
            entry = {}
            mgmt_ip = _get_mgmt_ip(dev, ip_addresses, mgmt_interface_name)
            if mgmt_ip:
                entry["ansible_host"] = mgmt_ip.split("/")[0]
            hosts[name] = entry or None
        dc_children[group_name] = {"hosts": hosts}
        if type_cfg.get("in_network_services"):
            ns_children[group_name] = None
        if type_cfg.get("in_connected_endpoints"):
            ce_children[group_name] = None

    inventory = {
        "all": {
            "children": {
                "FABRIC": {
                    "children": {
                        dc_name: {"children": dc_children},
                    }
                },
                network_services_name: {"children": ns_children},
                connected_endpoints_name: {"children": ce_children},
            }
        }
    }

    return inventory


def to_avd_multi_site_inventory(sites_devices, role_mapping,
                                ip_addresses=None,
                                mgmt_interface_name="Management0",
                                group_config=None):
    """Build AVD inventory for multiple sites (dual-dc, etc.)."""
    if not sites_devices:
        return {}

    ip_addresses = ip_addresses or []
    gc = group_config or DEFAULT_GROUP_CONFIG
    dc_children = {}
    ns_children = {}
    ce_children = {}

    for site_slug, devices in sorted(sites_devices.items()):
        dc_name = site_slug.upper().replace("-", "_")
        grouped = _group_devices_by_role(devices, role_mapping)
        site_children = {}

        for avd_type, devs in grouped.items():
            type_cfg = gc.get(avd_type)
            if not type_cfg:
                continue
            group_name = f"{dc_name}_{type_cfg['suffix']}"
            hosts = {}
            for dev in sorted(devs, key=lambda d: d.get("name", "")):
                name = dev.get("name")
                entry = {}
                mgmt_ip = _get_mgmt_ip(dev, ip_addresses,
                                       mgmt_interface_name)
                if mgmt_ip:
                    entry["ansible_host"] = mgmt_ip.split("/")[0]
                hosts[name] = entry or None
            site_children[group_name] = {"hosts": hosts}
            if type_cfg.get("in_network_services"):
                ns_children[group_name] = None
            if type_cfg.get("in_connected_endpoints"):
                ce_children[group_name] = None

        dc_children[dc_name] = {"children": site_children}

    return {
        "all": {
            "children": {
                "FABRIC": {"children": dc_children},
                "NETWORK_SERVICES": {"children": ns_children},
                "CONNECTED_ENDPOINTS": {"children": ce_children},
            }
        }
    }


def to_avd_spine_nodes(devices, ip_addresses=None, node_id_field="avd_node_id",
                       mgmt_interface_name="Management0"):
    """Convert NetBox spine devices to AVD spine node list.

    Returns:
        List of dicts: [{name, id, mgmt_ip}, ...]
    """
    ip_addresses = ip_addresses or []
    nodes = []
    for dev in sorted(devices, key=lambda d: d.get("name", "")):
        node = {"name": dev.get("name")}

        custom_fields = dev.get("custom_fields") or {}
        node_id = custom_fields.get(node_id_field)
        if node_id is not None:
            node["id"] = node_id

        mgmt_ip = _get_mgmt_ip(dev, ip_addresses, mgmt_interface_name)
        if mgmt_ip:
            node["mgmt_ip"] = mgmt_ip

        nodes.append(node)
    return nodes


def to_avd_spine_names(devices):
    """Extract sorted list of spine device names for uplink_switches."""
    return sorted(dev.get("name") for dev in devices if dev.get("name"))


def to_avd_l3leaf_node_groups(devices, defaults=None, ip_addresses=None,
                              node_id_field="avd_node_id",
                              node_group_field="avd_node_group",
                              mgmt_interface_name="Management0"):
    """Build AVD l3leaf node_groups by merging NetBox devices into defaults.

    Devices are grouped by their avd_node_group custom field. Each group's
    nodes list is injected into the matching defaults node_group entry.
    Groups found in NetBox but not in defaults get a new entry.

    Args:
        devices: List of NetBox l3leaf device dicts.
        defaults: Optional dict of l3leaf defaults (with node_groups).
        ip_addresses: Optional list of IP address dicts.
        node_id_field: Custom field name for node ID.
        node_group_field: Custom field name for node group.
        mgmt_interface_name: Management interface name.

    Returns:
        List of node_group dicts with nodes injected.
    """
    ip_addresses = ip_addresses or []
    defaults = defaults or {}

    groups_from_defaults = {}
    for ng in defaults.get("node_groups", []):
        group_name = ng.get("group")
        if group_name:
            groups_from_defaults[group_name] = copy.deepcopy(ng)

    groups_from_netbox = {}
    for dev in devices:
        custom_fields = dev.get("custom_fields") or {}
        group_name = custom_fields.get(node_group_field)
        if not group_name:
            continue
        groups_from_netbox.setdefault(group_name, []).append(dev)

    result = []
    seen_groups = set()

    for ng in defaults.get("node_groups", []):
        group_name = ng.get("group")
        if not group_name:
            continue
        seen_groups.add(group_name)
        entry = copy.deepcopy(ng)
        if group_name in groups_from_netbox:
            entry["nodes"] = _build_node_list(
                groups_from_netbox[group_name],
                ip_addresses,
                node_id_field,
                mgmt_interface_name,
            )
        result.append(entry)

    for group_name in sorted(groups_from_netbox.keys()):
        if group_name in seen_groups:
            continue
        entry = {
            "group": group_name,
            "nodes": _build_node_list(
                groups_from_netbox[group_name],
                ip_addresses,
                node_id_field,
                mgmt_interface_name,
            ),
        }
        bgp_as = _get_group_bgp_as(groups_from_netbox[group_name])
        if bgp_as is not None:
            entry["bgp_as"] = bgp_as
        result.append(entry)

    # Inject bgp_as from NetBox into defaults groups that don't have one
    for entry in result:
        if "bgp_as" not in entry:
            group_name = entry.get("group")
            if group_name and group_name in groups_from_netbox:
                bgp_as = _get_group_bgp_as(groups_from_netbox[group_name])
                if bgp_as is not None:
                    entry["bgp_as"] = bgp_as

    return result


def to_avd_l2leaf_node_groups(devices, defaults=None, ip_addresses=None,
                              node_id_field="avd_node_id",
                              node_group_field="avd_node_group",
                              mgmt_interface_name="Management0"):
    """Build AVD l2leaf node_groups. Same logic as l3leaf."""
    return to_avd_l3leaf_node_groups(
        devices, defaults, ip_addresses,
        node_id_field, node_group_field, mgmt_interface_name
    )


def to_avd_merge_defaults(base, override):
    """Public filter for deep-merging two dicts."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override if override is not None else base
    return _deep_merge(base, override)


def _build_node_list(devices, ip_addresses, node_id_field,
                     mgmt_interface_name):
    """Build a sorted list of AVD node entries from NetBox devices."""
    nodes = []
    for dev in sorted(devices, key=lambda d: d.get("name", "")):
        node = {"name": dev.get("name")}

        custom_fields = dev.get("custom_fields") or {}
        node_id = custom_fields.get(node_id_field)
        if node_id is not None:
            node["id"] = node_id

        mgmt_ip = _get_mgmt_ip(dev, ip_addresses, mgmt_interface_name)
        if mgmt_ip:
            node["mgmt_ip"] = mgmt_ip

        nodes.append(node)
    return nodes


def _get_group_bgp_as(devices, bgp_as_field="avd_bgp_as"):
    """Get BGP AS from the first device in a group that has one."""
    for dev in devices:
        cf = dev.get("custom_fields") or {}
        bgp_as = cf.get(bgp_as_field)
        if bgp_as is not None:
            try:
                return int(bgp_as)
            except (ValueError, TypeError):
                return bgp_as
    return None


def to_avd_ip_pools(prefixes, pool_role_field="avd_pool_role"):
    """Extract AVD IP pools from NetBox prefixes tagged with avd_pool_role.

    Returns a dict mapping pool role names to prefix strings:
    {
        "loopback": "10.255.0.0/27",
        "vtep": "10.255.1.0/27",
        "p2p_uplink": "10.255.255.0/26",
        "mlag_peer": "10.255.1.64/27",
        "mlag_peer_l3": "10.255.1.96/27",
    }
    """
    pools = {}
    for pfx in prefixes:
        cf = pfx.get("custom_fields") or {}
        role = cf.get(pool_role_field)
        if role:
            pools[role] = pfx.get("prefix")
    return pools


def _prefix_to_gateway(prefix_str):
    """Derive the .1 gateway IP from a prefix (e.g., 10.10.11.0/24 -> 10.10.11.1/24)."""
    if not prefix_str or "/" not in prefix_str:
        return None
    network, mask = prefix_str.split("/")
    parts = network.split(".")
    if len(parts) == 4:
        parts[3] = "1"
        return ".".join(parts) + "/" + mask
    return None


def to_avd_network_services(vlans, vrfs, prefixes, tenants,
                            defaults=None):
    """Build AVD network_services from NetBox VLANs, VRFs, prefixes, tenants.

    Groups VLANs by tenant -> VRF -> SVIs/L2VLANs.
    Prefixes assigned to VLANs provide ip_address_virtual.
    """
    defaults = defaults or {}

    prefix_by_vlan = {}
    for pfx in prefixes:
        vlan_obj = pfx.get("vlan")
        if vlan_obj and isinstance(vlan_obj, dict):
            vlan_id = vlan_obj.get("vid")
            if vlan_id:
                prefix_by_vlan[vlan_id] = pfx.get("prefix")

    vrf_by_name = {}
    for vrf in vrfs:
        name = vrf.get("name")
        if name:
            vrf_by_name[name] = vrf

    tenant_by_id = {}
    for t in tenants:
        tid = t.get("id")
        if tid:
            tenant_by_id[tid] = t

    tenant_data = {}
    for vlan in vlans:
        vid = vlan.get("vid")
        vlan_name = vlan.get("name") or f"VLAN{vid}"

        tenant_obj = vlan.get("tenant")
        if not tenant_obj:
            continue
        tenant_id = tenant_obj.get("id") if isinstance(tenant_obj, dict) else None
        tenant_name = _extract_name(tenant_obj)
        if not tenant_name:
            continue

        tenant_entry = tenant_data.setdefault(tenant_name, {
            "name": tenant_name,
            "tenant_id": tenant_id,
            "vrfs": {},
            "l2vlans": [],
        })

        vlan_has_vrf = False
        for vrf in vrfs:
            vrf_prefixes = [p for p in prefixes
                            if p.get("vrf") and isinstance(p["vrf"], dict)
                            and p["vrf"].get("name") == vrf.get("name")
                            and p.get("vlan") and isinstance(p["vlan"], dict)
                            and p["vlan"].get("vid") == vid]
            if vrf_prefixes:
                vrf_name = vrf.get("name")
                vrf_entry = tenant_entry["vrfs"].setdefault(vrf_name, {
                    "name": vrf_name,
                    "vrf_obj": vrf,
                    "svis": [],
                })
                svi = {"id": vid, "name": vlan_name, "enabled": True}
                gateway = _prefix_to_gateway(vrf_prefixes[0].get("prefix"))
                if gateway:
                    svi["ip_address_virtual"] = gateway
                vrf_entry["svis"].append(svi)
                vlan_has_vrf = True

        if not vlan_has_vrf:
            tenant_entry["l2vlans"].append({"id": vid, "name": vlan_name})

    result_tenants = []
    for t_name, t_data in sorted(tenant_data.items()):
        tenant_out = {"name": t_data["name"]}

        if t_data["tenant_id"] and t_data["tenant_id"] in tenant_by_id:
            t_obj = tenant_by_id[t_data["tenant_id"]]
            cf = t_obj.get("custom_fields") or {}
            base = cf.get("avd_mac_vrf_vni_base")
            if base is not None:
                tenant_out["mac_vrf_vni_base"] = base

        if t_data["vrfs"]:
            tenant_vrfs = []
            for vrf_name, vrf_data in sorted(t_data["vrfs"].items()):
                vrf_out = {"name": vrf_name}
                vrf_obj = vrf_data["vrf_obj"]
                cf = vrf_obj.get("custom_fields") or {}

                vrf_vni = cf.get("avd_vrf_vni")
                if vrf_vni is not None:
                    vrf_out["vrf_vni"] = vrf_vni

                diag_lo = cf.get("avd_vtep_diagnostic_loopback")
                diag_ip = cf.get("avd_vtep_diagnostic_loopback_ip_range")
                if diag_lo is not None:
                    vrf_out["vtep_diagnostic"] = {"loopback": diag_lo}
                    if diag_ip:
                        vrf_out["vtep_diagnostic"]["loopback_ip_range"] = diag_ip

                if vrf_data["svis"]:
                    vrf_out["svis"] = sorted(
                        vrf_data["svis"], key=lambda s: s["id"])
                tenant_vrfs.append(vrf_out)
            tenant_out["vrfs"] = tenant_vrfs

        if t_data["l2vlans"]:
            tenant_out["l2vlans"] = sorted(
                t_data["l2vlans"], key=lambda v: v["id"])

        result_tenants.append(tenant_out)

    result = {"tenants": result_tenants}
    if defaults:
        result = _deep_merge(defaults, result)
    return result


def to_avd_connected_endpoints(cables, interfaces, devices,
                               role_mapping=None):
    """Build AVD connected_endpoints from NetBox cables.

    Finds cables between non-network devices (servers) and network devices
    (leafs/spines), then builds the servers[] structure with adapters.
    """
    role_mapping = role_mapping or {
        "spine": "spine", "l3-leaf": "l3leaf", "l2-leaf": "l2leaf"
    }
    network_roles = set(role_mapping.keys())

    device_by_id = {}
    for dev in devices:
        device_by_id[dev.get("id")] = dev

    iface_by_id = {}
    for iface in interfaces:
        iface_by_id[iface.get("id")] = iface

    server_adapters = {}

    for cable in cables:
        a_terms = cable.get("a_terminations") or []
        b_terms = cable.get("b_terminations") or []
        if not a_terms or not b_terms:
            continue

        a_obj = a_terms[0].get("object", {})
        b_obj = b_terms[0].get("object", {})

        a_dev = a_obj.get("device", {})
        b_dev = b_obj.get("device", {})

        a_dev_full = device_by_id.get(a_dev.get("id"), {})
        b_dev_full = device_by_id.get(b_dev.get("id"), {})

        a_role = _extract_slug(a_dev_full.get("role"))
        b_role = _extract_slug(b_dev_full.get("role"))

        if a_role in network_roles and b_role not in network_roles:
            switch_obj, switch_iface = a_obj, a_obj
            server_obj, server_iface = b_obj, b_obj
        elif b_role in network_roles and a_role not in network_roles:
            switch_obj, switch_iface = b_obj, b_obj
            server_obj, server_iface = a_obj, a_obj
        else:
            continue

        server_name = _extract_name(server_obj.get("device"))
        if not server_name:
            continue

        sw_iface_full = iface_by_id.get(switch_iface.get("id"), {})
        ep_port = _extract_name(server_iface)
        sw_port = _extract_name(switch_iface)
        sw_name = _extract_name(switch_obj.get("device"))

        mode_val = _extract_value(sw_iface_full.get("mode"))
        tagged = sw_iface_full.get("tagged_vlans") or []
        untagged = sw_iface_full.get("untagged_vlan")
        lag = sw_iface_full.get("lag")

        adapter_key = server_name
        if lag:
            lag_name = _extract_name(lag)
            adapter_key = f"{server_name}:{lag_name}"

        adapters = server_adapters.setdefault(server_name, {})
        adapter = adapters.setdefault(adapter_key, {
            "endpoint_ports": [],
            "switch_ports": [],
            "switches": [],
            "mode": None,
            "vlans": set(),
            "native_vlan": None,
            "has_lag": lag is not None,
        })

        adapter["endpoint_ports"].append(ep_port)
        adapter["switch_ports"].append(sw_port)
        adapter["switches"].append(sw_name)

        if mode_val == "tagged":
            adapter["mode"] = "trunk"
            for tv in tagged:
                vid = tv.get("vid") if isinstance(tv, dict) else None
                if vid:
                    adapter["vlans"].add(vid)
            if untagged and isinstance(untagged, dict):
                adapter["native_vlan"] = untagged.get("vid")
        elif mode_val == "access":
            adapter["mode"] = "access"
            if untagged and isinstance(untagged, dict):
                adapter["vlans"].add(untagged.get("vid"))

    result = []
    for server_name in sorted(server_adapters.keys()):
        adapters_out = []
        for key, adapter in sorted(server_adapters[server_name].items()):
            entry = {
                "endpoint_ports": adapter["endpoint_ports"],
                "switch_ports": adapter["switch_ports"],
                "switches": adapter["switches"],
            }
            if adapter["vlans"]:
                entry["vlans"] = _format_vlan_range(sorted(adapter["vlans"]))
            if adapter["native_vlan"]:
                entry["native_vlan"] = adapter["native_vlan"]
            if adapter["mode"]:
                entry["mode"] = adapter["mode"]
            entry["spanning_tree_portfast"] = "edge"
            if adapter["has_lag"] and len(adapter["switches"]) > 1:
                entry["port_channel"] = {"mode": "active"}
            adapters_out.append(entry)
        result.append({"name": server_name, "adapters": adapters_out})

    return {"servers": result} if result else {}


def _format_vlan_range(vlan_ids):
    """Format sorted VLAN IDs into a compact range string (e.g., '11-12,21-22')."""
    if not vlan_ids:
        return ""
    ranges = []
    start = prev = vlan_ids[0]
    for vid in vlan_ids[1:]:
        if vid == prev + 1:
            prev = vid
        else:
            ranges.append(f"{start}-{prev}" if start != prev else str(start))
            start = prev = vid
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ",".join(ranges)


def to_avd_spine_bgp_as(devices, bgp_as_field="avd_bgp_as"):
    """Extract BGP AS from spine devices."""
    return _get_group_bgp_as(devices, bgp_as_field)


class FilterModule:
    """Jinja2 filters for transforming NetBox data to AVD structures."""

    def filters(self):
        return {
            "to_avd_inventory": to_avd_inventory,
            "to_avd_multi_site_inventory": to_avd_multi_site_inventory,
            "to_avd_spine_nodes": to_avd_spine_nodes,
            "to_avd_spine_names": to_avd_spine_names,
            "to_avd_l3leaf_node_groups": to_avd_l3leaf_node_groups,
            "to_avd_l2leaf_node_groups": to_avd_l2leaf_node_groups,
            "to_avd_merge_defaults": to_avd_merge_defaults,
            "to_avd_network_services": to_avd_network_services,
            "to_avd_connected_endpoints": to_avd_connected_endpoints,
            "to_avd_spine_bgp_as": to_avd_spine_bgp_as,
            "to_avd_ip_pools": to_avd_ip_pools,
        }
