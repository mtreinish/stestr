#!/bin/sh

mkdir -p doc/build/man
tox -evenv -- sphinx-build -b man doc/source doc/build/man
