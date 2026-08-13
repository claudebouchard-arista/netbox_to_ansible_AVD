from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from ansible.module_utils.urls import open_url


class NetBoxClient:
    """Lightweight REST client for the NetBox API."""

    def __init__(self, url, token, validate_certs=False):
        self.base_url = url.rstrip("/")
        self.token = token
        self.validate_certs = validate_certs
        self.headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, endpoint, params=None):
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}/"
        if params:
            query = "&".join(
                f"{k}={v}" for k, v in params.items() if v is not None
            )
            if query:
                url = f"{url}?{query}"
        response = open_url(
            url,
            headers=self.headers,
            validate_certs=self.validate_certs,
            method="GET",
        )
        return json.loads(response.read())

    def _get_all(self, endpoint, params=None):
        params = dict(params or {})
        params.setdefault("limit", 100)
        results = []
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}/"
        query = "&".join(
            f"{k}={v}" for k, v in params.items() if v is not None
        )
        if query:
            url = f"{url}?{query}"

        while url:
            response = open_url(
                url,
                headers=self.headers,
                validate_certs=self.validate_certs,
                method="GET",
            )
            data = json.loads(response.read())
            results.extend(data.get("results", []))
            url = data.get("next")
        return results

    def get_devices(self, role=None, site=None, status=None, tag=None):
        params = {}
        if role:
            params["role"] = role
        if site:
            params["site"] = site
        if status:
            params["status"] = status
        if tag:
            params["tag"] = tag
        return self._get_all("dcim/devices", params)

    def get_device(self, device_id):
        return self._get(f"dcim/devices/{device_id}")

    def get_interfaces(self, device_id):
        return self._get_all("dcim/interfaces", {"device_id": device_id})

    def get_ip_addresses(self, device_id=None, interface_id=None):
        params = {}
        if device_id:
            params["device_id"] = device_id
        if interface_id:
            params["interface_id"] = interface_id
        return self._get_all("ipam/ip-addresses", params)

    def get_sites(self, region=None, status=None, tag=None):
        params = {}
        if region:
            params["region"] = region
        if status:
            params["status"] = status
        if tag:
            params["tag"] = tag
        return self._get_all("dcim/sites", params)

    def get_vlans(self, site=None, group=None):
        params = {}
        if site:
            params["site"] = site
        if group:
            params["group"] = group
        return self._get_all("ipam/vlans", params)

    def get_vrfs(self, tenant=None):
        params = {}
        if tenant:
            params["tenant"] = tenant
        return self._get_all("ipam/vrfs", params)
