#!/usr/bin/env bash

set -ex

sudo rm -rf ./config/custom_components/rtask
sudo rm -rf ./config/www/community/rtask-card

cp -r ../../custom_components config/
cp -r ../../www config/

docker compose restart
docker compose logs -f
