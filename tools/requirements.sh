#!/bin/bash
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

set -o errexit -o pipefail -o nounset
shopt -s nullglob

if [[ $# -ne 1 ]]; then
    echo "Usage: $(basename "$0") SPEC"
    exit 2
fi

uv export --no-header --format=requirements.txt --script=<(
cat <<EOF
# /// script
# requires-python = '>=3.12'
# dependencies = ['$1']
# ///
EOF
)
