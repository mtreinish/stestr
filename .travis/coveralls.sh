#!/bin/sh

if [ "$TOXENV" = "cover" ]; then
    coverall
fi
