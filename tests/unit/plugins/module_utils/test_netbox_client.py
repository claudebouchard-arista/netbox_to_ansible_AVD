import json
from unittest.mock import MagicMock, patch

import pytest

from ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client import (
    NetBoxClient,
)

NETBOX_URL = "http://netbox:8000"
NETBOX_TOKEN = "test-token-12345"


@pytest.fixture
def client():
    return NetBoxClient(NETBOX_URL, NETBOX_TOKEN, validate_certs=False)


def _mock_response(data):
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    return resp


class TestNetBoxClientInit:
    def test_strips_trailing_slash(self):
        c = NetBoxClient("http://netbox:8000/", "token")
        assert c.base_url == "http://netbox:8000"

    def test_sets_auth_header(self):
        c = NetBoxClient(NETBOX_URL, "my-token")
        assert c.headers["Authorization"] == "Token my-token"


class TestGetDevices:
    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_basic_query(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 1, "next": None, "results": [{"id": 1, "name": "spine1"}]}
        )
        result = client.get_devices()
        assert len(result) == 1
        assert result[0]["name"] == "spine1"
        call_url = mock_open_url.call_args[0][0]
        assert "dcim/devices" in call_url

    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_with_filters(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 0, "next": None, "results": []}
        )
        client.get_devices(role="spine", site="dc1", status="active")
        call_url = mock_open_url.call_args[0][0]
        assert "role=spine" in call_url
        assert "site=dc1" in call_url
        assert "status=active" in call_url

    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_pagination(self, mock_open_url, client):
        page1 = _mock_response({
            "count": 3,
            "next": f"{NETBOX_URL}/api/dcim/devices/?limit=100&offset=2",
            "results": [{"id": 1}, {"id": 2}],
        })
        page2 = _mock_response({
            "count": 3, "next": None, "results": [{"id": 3}]
        })
        mock_open_url.side_effect = [page1, page2]
        result = client.get_devices()
        assert len(result) == 3
        assert mock_open_url.call_count == 2

    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_empty_results(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 0, "next": None, "results": []}
        )
        assert client.get_devices() == []

    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_tag_filter(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 0, "next": None, "results": []}
        )
        client.get_devices(tag="avd-managed")
        call_url = mock_open_url.call_args[0][0]
        assert "tag=avd-managed" in call_url


class TestGetDevice:
    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_single_device(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"id": 42, "name": "dc1-spine1"}
        )
        result = client.get_device(42)
        assert result["name"] == "dc1-spine1"
        call_url = mock_open_url.call_args[0][0]
        assert "dcim/devices/42" in call_url


class TestGetInterfaces:
    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_by_device_id(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 2, "next": None, "results": [
                {"id": 1, "name": "Ethernet1"},
                {"id": 2, "name": "Management0"},
            ]}
        )
        result = client.get_interfaces(device_id=10)
        assert len(result) == 2
        call_url = mock_open_url.call_args[0][0]
        assert "device_id=10" in call_url


class TestGetIPAddresses:
    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_by_device(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 1, "next": None, "results": [
                {"id": 1, "address": "172.16.1.11/24"}
            ]}
        )
        result = client.get_ip_addresses(device_id=5)
        assert result[0]["address"] == "172.16.1.11/24"

    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_by_interface(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 0, "next": None, "results": []}
        )
        client.get_ip_addresses(interface_id=99)
        call_url = mock_open_url.call_args[0][0]
        assert "interface_id=99" in call_url


class TestGetSites:
    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_all_sites(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 1, "next": None, "results": [
                {"id": 1, "name": "DC1", "slug": "dc1"}
            ]}
        )
        result = client.get_sites()
        assert result[0]["slug"] == "dc1"

    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_with_region(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 0, "next": None, "results": []}
        )
        client.get_sites(region="us-east")
        call_url = mock_open_url.call_args[0][0]
        assert "region=us-east" in call_url


class TestGetVlans:
    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_by_site(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 1, "next": None, "results": [
                {"id": 1, "vid": 10, "name": "VLAN10"}
            ]}
        )
        result = client.get_vlans(site="dc1")
        assert result[0]["vid"] == 10


class TestGetVrfs:
    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_all_vrfs(self, mock_open_url, client):
        mock_open_url.return_value = _mock_response(
            {"count": 1, "next": None, "results": [
                {"id": 1, "name": "VRF10"}
            ]}
        )
        result = client.get_vrfs()
        assert result[0]["name"] == "VRF10"


class TestCertValidation:
    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_validate_certs_passed(self, mock_open_url):
        mock_open_url.return_value = _mock_response(
            {"count": 0, "next": None, "results": []}
        )
        c = NetBoxClient(NETBOX_URL, NETBOX_TOKEN, validate_certs=True)
        c.get_devices()
        assert mock_open_url.call_args[1]["validate_certs"] is True

    @patch("ansible_collections.arista.netbox_avd.plugins.module_utils.netbox_client.open_url")
    def test_no_validate_certs(self, mock_open_url):
        mock_open_url.return_value = _mock_response(
            {"count": 0, "next": None, "results": []}
        )
        c = NetBoxClient(NETBOX_URL, NETBOX_TOKEN, validate_certs=False)
        c.get_devices()
        assert mock_open_url.call_args[1]["validate_certs"] is False
