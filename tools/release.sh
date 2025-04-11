#!/bin/bash
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

set -o errexit -o pipefail -o nounset
shopt -s nullglob

common="$(realpath "$(dirname "$0")/..")"
version="$(sed -rne "s/^__version__\\s*=\\s*'([^']+)'\\s*(#.*)?\$/\\1/p" \
             < "${common}/tdoc/common/__init__.py")"
previous="$(hg -R "${common}" tags --quiet | grep -vF 'tip' | head -n 1)"

echo "Version:  ${version}"
echo "Previous: ${previous}"
echo
hg -R "${common}" log --graph --rev="${previous}:tip"
echo
hg -R "${common}" diff

echo
read -r -p "Create release? " reply
if ! [[ "${reply}" =~ ^[yY] ]]; then
    echo "Aborted"
    exit 1
fi

hg -R "${common}" ci -m "Release ${version}."
hg -R "${common}" tag -m "Tag ${version} release." "${version}"
