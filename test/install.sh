#!/usr/bin/env bash

set -ex

rm -rf ./homeassistant/config/{custom_components,www}
cp -r ../custom_components ./homeassistant/config/
cp -r ../www ./homeassistant/config/
