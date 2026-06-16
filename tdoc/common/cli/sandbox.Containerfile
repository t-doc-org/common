# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

FROM docker.io/python:3-slim
RUN --mount=type=bind,source=/,dst=/mnt/ctx \
    set -o errexit; \
    useradd -K USERGROUPS_ENAB=yes --uid=1000 \
        --create-home --no-log-init user; \
    cp /mnt/ctx/sandbox.bashrc /root/.bashrc; \
    cp /mnt/ctx/sandbox.bashrc /home/user/.bashrc; \
    mkdir -p /etc/mercurial/hgrc.d; \
    cp /mnt/ctx/sandbox.hgrc /etc/mercurial/hgrc.d/tdoc.rc;
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
