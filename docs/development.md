# Development

## Dev Environment

The project includes a devcontainer for VS Code / GitHub Codespaces with all dependencies pre-installed.

### Manual Setup

```bash
pip install ansible-core pytest pytest-cov pytest-mock pynetbox requests pyavd
ansible-galaxy collection install arista.avd ansible.netcommon ansible.utils
```

## Makefile Targets

```
make help              # Show all targets
make lint              # flake8 + yamllint
make test-unit         # Unit tests with coverage
make test-integration  # Integration tests (requires NetBox)
make up                # Start NetBox Docker stack
make down              # Stop NetBox Docker stack
make seed              # Seed NetBox with test topology
make generate          # Generate sites/dc1 + AVD build
make verify            # Regenerate and diff against committed reference
make build             # Build collection tarball
make clean             # Remove build artifacts
```

## Testing

### Unit Tests

```bash
make test-unit
# 64 tests, 96% coverage
```

Unit tests cover all filter plugins and the NetBox client with mocked API responses. No Docker or NetBox required.

### Integration Tests

```bash
make up          # Start NetBox
make seed        # Seed test topology
make test-integration
# 17 tests against live NetBox
```

Tests verify:

- NetBox API connectivity and authentication
- All seeded data exists (devices, roles, VLANs, VRFs, custom fields, cables)
- Full transform pipeline: NetBox API responses → filter plugins → correct AVD structures

### Golden-File Verification

```bash
make verify
```

Regenerates `sites/dc1/` from NetBox and diffs against committed files. See [CI/CD](cicd.md).

## Adding a New Topology

To add support for a new AVD example (e.g., dual-dc-l3ls, campus):

1. **Study the AVD example** -- understand the expected `group_vars/` structure
2. **Extend the seeder** -- add new devices, roles, sites to `tests/fixtures/seed_netbox.py`
3. **Add/update filters** if the topology needs new transforms
4. **Create example defaults** -- `examples/<topology>/avd_defaults/`
5. **Create a site** -- `sites/<name>/` with generate playbook and committed output
6. **Add tests** -- unit tests for new filters, integration coverage for new topology
7. **Update CI** -- add verification step for the new site

## Project Structure

```
ansible_collections/arista/netbox_avd/
├── galaxy.yml                    # Collection metadata
├── plugins/
│   ├── filter/netbox_to_avd.py  # All transform filters
│   └── module_utils/
│       └── netbox_client.py     # NetBox REST client
├── roles/generate_avd/
│   ├── defaults/main.yml        # Role variables
│   └── tasks/
│       ├── main.yml             # Orchestrator
│       ├── query_netbox.yml     # API queries
│       ├── load_defaults.yml    # Read avd_defaults/
│       ├── transform.yml        # Apply filters
│       └── write_output.yml     # Write YAML files
├── examples/                    # Example defaults per topology
└── playbooks/                   # Ready-to-use playbooks
```

## Sister Projects

This collection follows the same patterns as:

- [netbox_to_ansible_velocloud](https://github.com/claudebouchard-arista/netbox_to_ansible_velocloud) -- NetBox → VeloCloud SD-WAN
- [netbox_to_ansible_cvcue](https://github.com/claudebouchard-arista/netbox_to_ansible_cvcue) -- NetBox → CV-CUE WiFi

All three share: Ansible collection structure, Jinja2 filter plugins, Docker NetBox test stack, idempotent seeders, and 4-job CI pipelines.
