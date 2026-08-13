import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests against a live NetBox instance",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return
    import os
    if os.environ.get("NETBOX_INTEGRATION", "").lower() in ("1", "true", "yes"):
        return
    skip_integration = pytest.mark.skip(
        reason="Need --run-integration or NETBOX_INTEGRATION=1"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
