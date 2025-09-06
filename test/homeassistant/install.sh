#!/usr/bin/env bash

set -ex

sudo rm -rf config/{custom_components,www}
cp -r ../../custom_components config/
cp -r ../../www config/

docker compose restart
