"""Integration tests against a live NetBox instance.

These tests require a running NetBox with the seeded AVD topology.
Run with: pytest --run-integration tests/integration/
Or set: NETBOX_INTEGRATION=1
"""
import os

import pytest
import requests

from ansible_collections.arista.netbox_avd.plugins.filter.netbox_to_avd import (
    to_avd_inventory,
    to_avd_l3leaf_node_groups,
    to_avd_l2leaf_node_groups,
    to_avd_spine_names,
    to_avd_spine_nodes,
)

NETBOX_URL = os.environ.get("NETBOX_URL", "http://localhost:18080")
NETBOX_TOKEN = os.environ.get(
    "NETBOX_TOKEN", "0123456789abcdef0123456789abcdef01234567"
)

ROLE_MAPPING = {
    "spine": "spine",
    "l3-leaf": "l3leaf",
    "l2-leaf": "l2leaf",
}


def _api_get(endpoint, params=None):
    url = f"{NETBOX_URL}/api/{endpoint}/"
    headers = {
        "Authorization": f"Token {NETBOX_TOKEN}",
        "Accept": "application/json",
    }
    resp = requests.get(url, headers=headers, params=params or {})
    resp.raise_for_status()
    return resp.json()


@pytest.fixture(scope="module")
def netbox_devices():
    data = _api_get("dcim/devices", {"site": "dc1", "status": "active", "limit": 1000})
    return data["results"]


@pytest.fixture(scope="module")
def netbox_ip_addresses(netbox_devices):
    all_ips = []
    for dev in netbox_devices:
        data = _api_get("ipam/ip-addresses", {"device_id": dev["id"], "limit": 1000})
        all_ips.extend(data["results"])
    return all_ips


@pytest.mark.integration
class TestNetBoxConnectivity:
    def test_api_reachable(self):
        resp = requests.get(
            f"{NETBOX_URL}/api/",
            headers={"Authorization": f"Token {NETBOX_TOKEN}"},
        )
        assert resp.status_code == 200

    def test_authenticated(self):
        data = _api_get("dcim/sites")
        assert "results" in data


@pytest.mark.integration
class TestSeededData:
    def test_site_exists(self):
        data = _api_get("dcim/sites", {"slug": "dc1"})
        assert data["count"] >= 1
        assert data["results"][0]["name"] == "DC1"

    def test_device_roles_exist(self):
        for slug in ["spine", "l3-leaf", "l2-leaf"]:
            data = _api_get("dcim/device-roles", {"slug": slug})
            assert data["count"] >= 1, f"Role '{slug}' not found"

    def test_device_count(self, netbox_devices):
        assert len(netbox_devices) == 8

    def test_spine_devices(self, netbox_devices):
        spines = [d for d in netbox_devices if d["role"]["slug"] == "spine"]
        assert len(spines) == 2
        names = {d["name"] for d in spines}
        assert names == {"dc1-spine1", "dc1-spine2"}

    def test_l3leaf_devices(self, netbox_devices):
        l3leafs = [d for d in netbox_devices if d["role"]["slug"] == "l3-leaf"]
        assert len(l3leafs) == 4
        names = {d["name"] for d in l3leafs}
        assert names == {"dc1-leaf1a", "dc1-leaf1b", "dc1-leaf2a", "dc1-leaf2b"}

    def test_l2leaf_devices(self, netbox_devices):
        l2leafs = [d for d in netbox_devices if d["role"]["slug"] == "l2-leaf"]
        assert len(l2leafs) == 2
        names = {d["name"] for d in l2leafs}
        assert names == {"dc1-leaf1c", "dc1-leaf2c"}

    def test_custom_fields_exist(self, netbox_devices):
        for dev in netbox_devices:
            cf = dev.get("custom_fields", {})
            assert "avd_node_id" in cf, f"{dev['name']} missing avd_node_id"
            assert cf["avd_node_id"] is not None, f"{dev['name']} has null node_id"

    def test_l3leaf_node_groups(self, netbox_devices):
        l3leafs = [d for d in netbox_devices if d["role"]["slug"] == "l3-leaf"]
        groups = set()
        for dev in l3leafs:
            g = dev.get("custom_fields", {}).get("avd_node_group")
            assert g, f"{dev['name']} missing avd_node_group"
            groups.add(g)
        assert groups == {"DC1_L3_LEAF1", "DC1_L3_LEAF2"}

    def test_management_ips(self, netbox_ip_addresses):
        assert len(netbox_ip_addresses) >= 8


@pytest.mark.integration
class TestFullPipeline:
    def test_inventory_generation(self, netbox_devices, netbox_ip_addresses):
        result = to_avd_inventory(
            netbox_devices, "dc1", ROLE_MAPPING, netbox_ip_addresses
        )
        assert "all" in result
        fabric = result["all"]["children"]["FABRIC"]
        dc1 = fabric["children"]["DC1"]["children"]
        assert "DC1_SPINES" in dc1
        assert "DC1_L3_LEAVES" in dc1
        assert "DC1_L2_LEAVES" in dc1

        spines = dc1["DC1_SPINES"]["hosts"]
        assert "dc1-spine1" in spines
        assert spines["dc1-spine1"]["ansible_host"] == "172.16.1.11"

    def test_spine_nodes(self, netbox_devices, netbox_ip_addresses):
        spines = [d for d in netbox_devices if d["role"]["slug"] == "spine"]
        result = to_avd_spine_nodes(spines, netbox_ip_addresses)
        assert len(result) == 2
        assert result[0]["name"] == "dc1-spine1"
        assert result[0]["id"] == 1
        assert result[0]["mgmt_ip"] == "172.16.1.11/24"

    def test_spine_names(self, netbox_devices):
        spines = [d for d in netbox_devices if d["role"]["slug"] == "spine"]
        result = to_avd_spine_names(spines)
        assert result == ["dc1-spine1", "dc1-spine2"]

    def test_l3leaf_node_groups(self, netbox_devices, netbox_ip_addresses):
        l3leafs = [d for d in netbox_devices if d["role"]["slug"] == "l3-leaf"]
        defaults = {
            "node_groups": [
                {"group": "DC1_L3_LEAF1", "bgp_as": 65101},
                {"group": "DC1_L3_LEAF2", "bgp_as": 65102},
            ]
        }
        result = to_avd_l3leaf_node_groups(
            l3leafs, defaults, netbox_ip_addresses
        )
        assert len(result) == 2

        leaf1 = result[0]
        assert leaf1["group"] == "DC1_L3_LEAF1"
        assert leaf1["bgp_as"] == 65101
        assert len(leaf1["nodes"]) == 2
        names = [n["name"] for n in leaf1["nodes"]]
        assert "dc1-leaf1a" in names
        assert "dc1-leaf1b" in names

        leaf2 = result[1]
        assert leaf2["group"] == "DC1_L3_LEAF2"
        assert leaf2["bgp_as"] == 65102
        assert len(leaf2["nodes"]) == 2

    def test_l2leaf_node_groups(self, netbox_devices, netbox_ip_addresses):
        l2leafs = [d for d in netbox_devices if d["role"]["slug"] == "l2-leaf"]
        defaults = {
            "node_groups": [
                {
                    "group": "DC1_L2_LEAF1",
                    "uplink_switches": ["dc1-leaf1a", "dc1-leaf1b"],
                },
                {
                    "group": "DC1_L2_LEAF2",
                    "uplink_switches": ["dc1-leaf2a", "dc1-leaf2b"],
                },
            ]
        }
        result = to_avd_l2leaf_node_groups(
            l2leafs, defaults, netbox_ip_addresses
        )
        assert len(result) == 2
        assert result[0]["nodes"][0]["name"] == "dc1-leaf1c"
        assert result[0]["uplink_switches"] == ["dc1-leaf1a", "dc1-leaf1b"]
        assert result[1]["nodes"][0]["name"] == "dc1-leaf2c"

    def test_full_inventory_structure(self, netbox_devices, netbox_ip_addresses):
        result = to_avd_inventory(
            netbox_devices, "dc1", ROLE_MAPPING, netbox_ip_addresses
        )
        ns = result["all"]["children"]["NETWORK_SERVICES"]["children"]
        assert "DC1_L3_LEAVES" in ns
        assert "DC1_L2_LEAVES" in ns

        ce = result["all"]["children"]["CONNECTED_ENDPOINTS"]["children"]
        assert "DC1_L3_LEAVES" in ce
        assert "DC1_L2_LEAVES" in ce
