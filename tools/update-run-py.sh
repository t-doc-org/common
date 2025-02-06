#!/bin/bash
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

common="$(realpath "$(dirname $0)/..")"
src="${common}/run.py"
for dest in "${common}/../"*"/run.py"; do
    [[ "${src}" -ef "${dest}" ]] && continue
    echo "${src} -> ${dest}"
    cp "${src}" "${dest}"
done
