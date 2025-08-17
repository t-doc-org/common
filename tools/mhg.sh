#!/bin/bash
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

set -o errexit -o pipefail -o nounset
shopt -s nullglob

base="$(realpath "$(dirname "$0")/../..")"
for repo in "${base}/"*; do
    [[ -d "${repo}/.hg" ]] || continue
    echo "==== ${repo}"
    hg --repository "${repo}" --cwd "${repo}" "$@" || true
done
