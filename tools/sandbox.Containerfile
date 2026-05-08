# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

FROM docker.io/python:3-slim
RUN --mount=type=bind,source=/,dst=/mnt/ctx \
    useradd -K USERGROUPS_ENAB=yes --uid=1000 --create-home user && \
    cp /mnt/ctx/bashrc /root/.bashrc && \
    cp /mnt/ctx/bashrc /home/user/.bashrc && \
    python -P -m pip install build && \
    apt-get update && \
    apt-get install --yes --no-install-recommends \
        graphviz npm && \
    rm -rf /var/lib/apt/lists/*
ENV TDOC_DEFAULT_PORT=9000
