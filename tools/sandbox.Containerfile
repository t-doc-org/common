# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

FROM docker.io/python:3-slim
RUN --mount=type=bind,source=/,dst=/mnt/tools \
    set -o errexit; \
    useradd -K USERGROUPS_ENAB=yes --uid=1000 \
        --create-home --no-log-init user; \
    cp /mnt/tools/bashrc /root/.bashrc; \
    cp /mnt/tools/bashrc /home/user/.bashrc;
RUN --mount=type=bind,from=config,source=/,dst=/mnt/config \
    set -o errexit; \
    for pkg in build uv; do \
        python -P -m pip install --root-user-action=ignore \
            --require-hashes --only-binary=:all: --no-deps \
            --requirement="/mnt/config/${pkg}.req"; \
    done;
RUN \
    set -o errexit; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade \
        --yes --no-install-recommends; \
    DEBIAN_FRONTEND=noninteractive apt-get install \
        --yes --no-install-recommends \
        git graphviz less mercurial nodejs npm; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*;
