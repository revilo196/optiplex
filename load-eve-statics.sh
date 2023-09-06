#!/bin/bash

# make dir
mkdir optiplex/import

# load premade db
# curl https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2 | tar -xjC optiplex/import/

# load offical static data
curl https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip > /tmp/sde.zip
unzip /tmp/sde.zip -d optiplex/import/

# outdated items are used from upto date CCP-server instead
# load icons
curl https://content.eveonline.com/data/Invasion_1.0_Icons.zip > /tmp/items.zip
unzip /tmp/items.zip -d optiplex/static/


