FROM mcr.microsoft.com/devcontainers/python:3.11

ARG ANSIBLE_CORE_VERSION=2.16.12

RUN pip install --no-cache-dir \
    ansible-core==${ANSIBLE_CORE_VERSION} \
    pytest \
    pytest-cov \
    pytest-mock \
    flake8 \
    pylint \
    yamllint \
    black \
    isort \
    jmespath \
    requests

RUN apt-get update && apt-get install -y --no-install-recommends \
    jq \
    && rm -rf /var/lib/apt/lists/*

RUN ansible-galaxy collection install \
    ansible.netcommon \
    ansible.utils \
    --force

RUN mkdir -p /home/vscode/.local/share /home/vscode/.local/bin /home/vscode/.claude \
    && chown -R vscode:vscode /home/vscode/.local /home/vscode/.claude

RUN pip install --no-cache-dir pynetbox>=7.0.0

WORKDIR /workspaces/netbox_to_ansible_AVD
