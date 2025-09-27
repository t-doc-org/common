#!/bin/bash
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

set -o errexit -o pipefail -o nounset
shopt -s nullglob

common="$(realpath "$(dirname "$0")/..")"

cd "${common}"
for v in "$@"; do
    reqs="${common}/config/${v}.req"
    uv export --no-header --format=requirements.txt --script=<(
        cat <<EOF
# /// script
# requires-python = '>=3.12'
# dependencies = ['t-doc-common==${v}']
# ///
EOF
        ) | sed -r -n -e '/^t-doc-common==/,/^[^ ]/{/^(t-doc-common==| )/p}' \
        > "${reqs}"
    uv export --no-header --format=requirements.txt --no-emit-project \
        >> "${reqs}"
done
