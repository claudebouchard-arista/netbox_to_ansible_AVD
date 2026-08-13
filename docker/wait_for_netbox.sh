#!/bin/bash
set -e

NETBOX_URL="${NETBOX_URL:-http://localhost:18080}"
MAX_WAIT="${MAX_WAIT:-300}"
INTERVAL=5

echo "Waiting for NetBox at ${NETBOX_URL} (max ${MAX_WAIT}s)..."

elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if curl -sf "${NETBOX_URL}/login/" > /dev/null 2>&1; then
        echo "NetBox is ready after ${elapsed}s"
        exit 0
    fi
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
    echo "  ...waiting (${elapsed}s / ${MAX_WAIT}s)"
done

echo "ERROR: NetBox did not become ready within ${MAX_WAIT}s"
exit 1
