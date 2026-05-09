# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

FROM docker.io/python:3-slim
RUN --mount=type=bind,source=/,dst=/mnt/ctx \
    useradd -K USERGROUPS_ENAB=yes --uid=1000 \
        --create-home --no-log-init user && \
    cp /mnt/ctx/bashrc /root/.bashrc && \
    cp /mnt/ctx/bashrc /home/user/.bashrc && \
    python -P -m pip install build && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade \
        --yes --no-install-recommends && \
    DEBIAN_FRONTEND=noninteractive apt-get install \
        --yes --no-install-recommends \
        git graphviz mercurial npm && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
