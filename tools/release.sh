#!/bin/bash
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

set -o errexit -o pipefail -o nounset
shopt -s nullglob

if [[ $# != 1 ]]; then
    echo "Usage: $(basename "$0") VERSION" >&2
    exit 1
fi
VERSION="$1"

hg ci -m "Release ${VERSION}."
hg tag -m "Tag ${VERSION} release." "${VERSION}"
