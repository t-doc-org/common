#!/bin/bash
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

set -o errexit -o pipefail -o nounset
shopt -s nullglob

common="$(realpath "$(dirname "$0")/..")"
version="$(sed -rne "s/^__version__\\s*=\\s*'([^']+)'\\s*(#.*)?\$/\\1/p" \
             < "${common}/tdoc/common/__init__.py")"
previous="$(hg -R "${common}" tags --quiet | grep -vF 'tip' | head -n 1)"

echo "Previous: ${previous}"
echo "Release:  ${version}"
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
hg -R "${common}" push

cat <<EOF

Next steps:
 - Increment __version__ in tdoc/common/__init__.py and add a ".dev1" suffix.
 - Wait for the package to be built and pushed to PyPI.
   https://github.com/t-doc-org/common/actions/workflows/package.yml
 - Generate the requirements file for the release, add the new file, commit and
   push.
   $ tools/release-reqs.sh ${version}
   $ hg add config/${version}.req
   $ hg commit -m "Add requirements for ${version}." \\
       tdoc/common/__init__.py config/${version}.req
   $ hg push
 - In config/t-doc.toml, move the current value of "stable" to "previous", set
   "stable" to ${version}, commit and push.
   $ hg commit -m "Roll out ${version} to stable." config/t-doc.toml
   $ hg push
EOF
