from ansible_collections.arista.netbox_avd.plugins.filter.netbox_to_avd import (
    FilterModule,
    _deep_merge,
    _extract_name,
    _extract_slug,
    _extract_value,
    _get_mgmt_ip,
    to_avd_inventory,
    to_avd_l3leaf_node_groups,
    to_avd_l2leaf_node_groups,
    to_avd_merge_defaults,
    to_avd_spine_names,
    to_avd_spine_nodes,
)

ROLE_MAPPING = {
    "spine": "spine",
    "l3-leaf": "l3leaf",
    "l2-leaf": "l2leaf",
}


def _make_device(name, role_slug, node_id=None, node_group=None,
                 primary_ip4=None):
    dev = {
        "id": hash(name) % 10000,
        "name": name,
        "role": {"name": role_slug.replace("-", " ").title(), "slug": role_slug},
        "custom_fields": {},
    }
    if node_id is not None:
        dev["custom_fields"]["avd_node_id"] = node_id
    if node_group is not None:
        dev["custom_fields"]["avd_node_group"] = node_group
    if primary_ip4:
        dev["primary_ip4"] = {"address": primary_ip4}
    return dev


def _make_ip(address, device_id, interface_name="Management0"):
    return {
        "address": address,
        "assigned_object": {
            "name": interface_name,
            "device": {"id": device_id},
        },
    }


# --- Helper tests ---

class TestExtractName:
    def test_dict_with_name(self):
        assert _extract_name({"name": "DC1", "id": 1}) == "DC1"

    def test_dict_with_display(self):
        assert _extract_name({"display": "My Site"}) == "My Site"

    def test_string(self):
        assert _extract_name("simple") == "simple"

    def test_none(self):
        assert _extract_name(None) is None


class TestExtractSlug:
    def test_dict_with_slug(self):
        assert _extract_slug({"slug": "l3-leaf", "name": "L3 Leaf"}) == "l3-leaf"

    def test_dict_with_value(self):
        assert _extract_slug({"value": "active"}) == "active"

    def test_string(self):
        assert _extract_slug("spine") == "spine"

    def test_none(self):
        assert _extract_slug(None) is None


class TestExtractValue:
    def test_dict_with_value(self):
        assert _extract_value({"value": "active", "label": "Active"}) == "active"

    def test_dict_with_label_only(self):
        assert _extract_value({"label": "Active"}) == "Active"

    def test_string(self):
        assert _extract_value("active") == "active"

    def test_none(self):
        assert _extract_value(None) is None


class TestGetMgmtIp:
    def test_from_ip_addresses(self):
        dev = _make_device("spine1", "spine")
        ips = [_make_ip("172.16.1.11/24", dev["id"], "Management0")]
        assert _get_mgmt_ip(dev, ips) == "172.16.1.11/24"

    def test_fallback_to_primary_ip4(self):
        dev = _make_device("spine1", "spine", primary_ip4="10.0.0.1/32")
        assert _get_mgmt_ip(dev, []) == "10.0.0.1/32"

    def test_no_ip_returns_none(self):
        dev = _make_device("spine1", "spine")
        assert _get_mgmt_ip(dev, []) is None

    def test_wrong_interface_name(self):
        dev = _make_device("spine1", "spine")
        ips = [_make_ip("172.16.1.11/24", dev["id"], "Loopback0")]
        assert _get_mgmt_ip(dev, ips, "Management0") is None

    def test_custom_interface_name(self):
        dev = _make_device("spine1", "spine")
        ips = [_make_ip("172.16.1.11/24", dev["id"], "Management1")]
        assert _get_mgmt_ip(dev, ips, "Management1") == "172.16.1.11/24"


class TestDeepMerge:
    def test_simple_merge(self):
        assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_override(self):
        assert _deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_nested_merge(self):
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"c": 3, "d": 4}}
        assert _deep_merge(base, override) == {"a": {"b": 1, "c": 3, "d": 4}}

    def test_does_not_mutate_base(self):
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}
        _deep_merge(base, override)
        assert base == {"a": {"b": 1}}

    def test_empty_override(self):
        assert _deep_merge({"a": 1}, {}) == {"a": 1}

    def test_empty_base(self):
        assert _deep_merge({}, {"a": 1}) == {"a": 1}


# --- Filter tests ---

class TestToAvdInventory:
    def test_basic_inventory(self):
        devices = [
            _make_device("dc1-spine1", "spine"),
            _make_device("dc1-spine2", "spine"),
            _make_device("dc1-leaf1a", "l3-leaf"),
            _make_device("dc1-leaf1b", "l3-leaf"),
            _make_device("dc1-leaf1c", "l2-leaf"),
        ]
        result = to_avd_inventory(devices, "dc1", ROLE_MAPPING)

        all_children = result["all"]["children"]
        assert "FABRIC" in all_children
        dc = all_children["FABRIC"]["children"]["DC1"]
        assert "DC1_SPINES" in dc["children"]
        assert "DC1_L3_LEAVES" in dc["children"]
        assert "DC1_L2_LEAVES" in dc["children"]

        spines = dc["children"]["DC1_SPINES"]["hosts"]
        assert "dc1-spine1" in spines
        assert "dc1-spine2" in spines

        l3leaves = dc["children"]["DC1_L3_LEAVES"]["hosts"]
        assert "dc1-leaf1a" in l3leaves
        assert "dc1-leaf1b" in l3leaves

    def test_with_management_ips(self):
        devices = [_make_device("dc1-spine1", "spine")]
        ips = [_make_ip("172.16.1.11/24", devices[0]["id"])]
        result = to_avd_inventory(devices, "dc1", ROLE_MAPPING, ips)
        host = result["all"]["children"]["FABRIC"]["children"]["DC1"][
            "children"]["DC1_SPINES"]["hosts"]["dc1-spine1"]
        assert host["ansible_host"] == "172.16.1.11"

    def test_network_services_and_connected_endpoints(self):
        devices = [
            _make_device("dc1-leaf1a", "l3-leaf"),
            _make_device("dc1-leaf1c", "l2-leaf"),
        ]
        result = to_avd_inventory(devices, "dc1", ROLE_MAPPING)
        ns = result["all"]["children"]["NETWORK_SERVICES"]["children"]
        assert "DC1_L3_LEAVES" in ns
        assert "DC1_L2_LEAVES" in ns
        ce = result["all"]["children"]["CONNECTED_ENDPOINTS"]["children"]
        assert "DC1_L3_LEAVES" in ce
        assert "DC1_L2_LEAVES" in ce

    def test_empty_devices(self):
        assert to_avd_inventory([], "dc1", ROLE_MAPPING) == {}

    def test_site_name_uppercase(self):
        devices = [_make_device("s1", "spine")]
        result = to_avd_inventory(devices, "my-site", ROLE_MAPPING)
        dc = result["all"]["children"]["FABRIC"]["children"]
        assert "MY_SITE" in dc

    def test_unknown_role_ignored(self):
        devices = [
            _make_device("dc1-spine1", "spine"),
            _make_device("dc1-fw1", "firewall"),
        ]
        result = to_avd_inventory(devices, "dc1", ROLE_MAPPING)
        dc = result["all"]["children"]["FABRIC"]["children"]["DC1"]["children"]
        assert "DC1_SPINES" in dc
        assert len(dc) == 1

    def test_spines_only_no_network_services(self):
        devices = [_make_device("dc1-spine1", "spine")]
        result = to_avd_inventory(devices, "dc1", ROLE_MAPPING)
        ns = result["all"]["children"]["NETWORK_SERVICES"]["children"]
        assert ns == {}


class TestToAvdSpineNodes:
    def test_basic(self):
        devices = [
            _make_device("dc1-spine2", "spine", node_id=2),
            _make_device("dc1-spine1", "spine", node_id=1),
        ]
        ips = [
            _make_ip("172.16.1.12/24", devices[0]["id"]),
            _make_ip("172.16.1.11/24", devices[1]["id"]),
        ]
        result = to_avd_spine_nodes(devices, ips)
        assert len(result) == 2
        assert result[0]["name"] == "dc1-spine1"
        assert result[0]["id"] == 1
        assert result[0]["mgmt_ip"] == "172.16.1.11/24"
        assert result[1]["name"] == "dc1-spine2"

    def test_no_custom_fields(self):
        devices = [_make_device("spine1", "spine")]
        result = to_avd_spine_nodes(devices)
        assert result[0]["name"] == "spine1"
        assert "id" not in result[0]
        assert "mgmt_ip" not in result[0]

    def test_empty(self):
        assert to_avd_spine_nodes([]) == []


class TestToAvdSpineNames:
    def test_sorted_names(self):
        devices = [
            _make_device("dc1-spine2", "spine"),
            _make_device("dc1-spine1", "spine"),
        ]
        assert to_avd_spine_names(devices) == ["dc1-spine1", "dc1-spine2"]

    def test_empty(self):
        assert to_avd_spine_names([]) == []


class TestToAvdL3LeafNodeGroups:
    def test_merge_with_defaults(self):
        devices = [
            _make_device("dc1-leaf1a", "l3-leaf", node_id=1, node_group="DC1_L3_LEAF1"),
            _make_device("dc1-leaf1b", "l3-leaf", node_id=2, node_group="DC1_L3_LEAF1"),
            _make_device("dc1-leaf2a", "l3-leaf", node_id=3, node_group="DC1_L3_LEAF2"),
            _make_device("dc1-leaf2b", "l3-leaf", node_id=4, node_group="DC1_L3_LEAF2"),
        ]
        ips = [
            _make_ip("172.16.1.101/24", devices[0]["id"]),
            _make_ip("172.16.1.102/24", devices[1]["id"]),
            _make_ip("172.16.1.103/24", devices[2]["id"]),
            _make_ip("172.16.1.104/24", devices[3]["id"]),
        ]
        defaults = {
            "node_groups": [
                {"group": "DC1_L3_LEAF1", "bgp_as": 65101},
                {"group": "DC1_L3_LEAF2", "bgp_as": 65102},
            ]
        }
        result = to_avd_l3leaf_node_groups(devices, defaults, ips)

        assert len(result) == 2
        assert result[0]["group"] == "DC1_L3_LEAF1"
        assert result[0]["bgp_as"] == 65101
        assert len(result[0]["nodes"]) == 2
        assert result[0]["nodes"][0]["name"] == "dc1-leaf1a"
        assert result[0]["nodes"][0]["id"] == 1
        assert result[0]["nodes"][0]["mgmt_ip"] == "172.16.1.101/24"

        assert result[1]["group"] == "DC1_L3_LEAF2"
        assert result[1]["bgp_as"] == 65102
        assert len(result[1]["nodes"]) == 2

    def test_no_defaults(self):
        devices = [
            _make_device("leaf1a", "l3-leaf", node_id=1, node_group="GROUP1"),
        ]
        result = to_avd_l3leaf_node_groups(devices)
        assert len(result) == 1
        assert result[0]["group"] == "GROUP1"
        assert len(result[0]["nodes"]) == 1
        assert result[0]["nodes"][0]["name"] == "leaf1a"

    def test_device_without_node_group_skipped(self):
        devices = [
            _make_device("leaf1a", "l3-leaf", node_id=1),
        ]
        result = to_avd_l3leaf_node_groups(devices)
        assert result == []

    def test_defaults_group_without_matching_devices(self):
        defaults = {
            "node_groups": [
                {"group": "EMPTY_GROUP", "bgp_as": 65199},
            ]
        }
        result = to_avd_l3leaf_node_groups([], defaults)
        assert len(result) == 1
        assert result[0]["group"] == "EMPTY_GROUP"
        assert result[0]["bgp_as"] == 65199
        assert "nodes" not in result[0]

    def test_new_group_from_netbox(self):
        devices = [
            _make_device("leaf3a", "l3-leaf", node_id=1, node_group="NEW_GROUP"),
        ]
        defaults = {
            "node_groups": [
                {"group": "OLD_GROUP", "bgp_as": 65101},
            ]
        }
        result = to_avd_l3leaf_node_groups(devices, defaults)
        assert len(result) == 2
        assert result[0]["group"] == "OLD_GROUP"
        assert result[1]["group"] == "NEW_GROUP"
        assert len(result[1]["nodes"]) == 1

    def test_preserves_extra_defaults_fields(self):
        devices = [
            _make_device("leaf1a", "l3-leaf", node_id=1, node_group="G1"),
        ]
        defaults = {
            "node_groups": [
                {"group": "G1", "bgp_as": 65101, "filter": {"tenants": ["ALL"]}},
            ]
        }
        result = to_avd_l3leaf_node_groups(devices, defaults)
        assert result[0]["filter"] == {"tenants": ["ALL"]}

    def test_does_not_mutate_defaults(self):
        devices = [
            _make_device("leaf1a", "l3-leaf", node_id=1, node_group="G1"),
        ]
        defaults = {"node_groups": [{"group": "G1", "bgp_as": 65101}]}
        to_avd_l3leaf_node_groups(devices, defaults)
        assert "nodes" not in defaults["node_groups"][0]


class TestToAvdL2LeafNodeGroups:
    def test_same_as_l3leaf(self):
        devices = [
            _make_device("dc1-leaf1c", "l2-leaf", node_id=1, node_group="DC1_L2_LEAF1"),
        ]
        defaults = {
            "node_groups": [
                {"group": "DC1_L2_LEAF1", "uplink_switches": ["dc1-leaf1a", "dc1-leaf1b"]},
            ]
        }
        ips = [_make_ip("172.16.1.151/24", devices[0]["id"])]
        result = to_avd_l2leaf_node_groups(devices, defaults, ips)
        assert len(result) == 1
        assert result[0]["uplink_switches"] == ["dc1-leaf1a", "dc1-leaf1b"]
        assert result[0]["nodes"][0]["name"] == "dc1-leaf1c"
        assert result[0]["nodes"][0]["mgmt_ip"] == "172.16.1.151/24"


class TestToAvdMergeDefaults:
    def test_dict_merge(self):
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"d": 3}}
        result = to_avd_merge_defaults(base, override)
        assert result == {"a": 1, "b": {"c": 2, "d": 3}}

    def test_non_dict_returns_override(self):
        assert to_avd_merge_defaults("a", "b") == "b"

    def test_none_override_returns_base(self):
        assert to_avd_merge_defaults({"a": 1}, None) == {"a": 1}


class TestFilterModule:
    def test_all_filters_registered(self):
        fm = FilterModule()
        filters = fm.filters()
        expected = [
            "to_avd_inventory",
            "to_avd_spine_nodes",
            "to_avd_spine_names",
            "to_avd_l3leaf_node_groups",
            "to_avd_l2leaf_node_groups",
            "to_avd_merge_defaults",
        ]
        for name in expected:
            assert name in filters, f"Filter '{name}' not registered"
