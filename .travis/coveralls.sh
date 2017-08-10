#!/bin/sh

python --version

if [ "$TOXENV" = "cover" ]; then
    coveralls
fi
