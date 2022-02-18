# Optiplex

## Requirements
- see requirements.txt

## Setup:

run the `load-eve-statics.sh` to load static data and icons from [dev.eve](https://developers.eveonline.com/resource)

run the command `flask init-db` to convert the downloaded data into sqlite and prepare it for later usage.

## Deployment \[WIP\]:
 for now only development deployment without proper server.
 just build the docker like this:
 ``` bash
  docker build --tag optiplex:latest .
 ```
 then run the docker or use docker-compose to use with traefik or similar
