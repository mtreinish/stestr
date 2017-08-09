#!/bin/sh

python --version

if [ "$TOXENV" = "cover" ]; then
    coverall
fi
