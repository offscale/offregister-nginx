offregister_nginx
================
This package follows the [offregister](https://github.com/offscale/offregister) specification to setup and serve nginx.

## Install dependencies

    pip install -r requirements.txt

## Install package

    pip install .

## Configuration options
### `nginx-init-name`
#### Default: `nginx.conf`
### `nginx-init-dir`
#### Default: `/etc/init`
### `nginx-upstart-filename`
#### Default: `offregister_nginx/conf/nginx.upstart.conf`

### `nginx-init-context`
With the following keys:
#### `AUTHOR`

#### `DESCRIPTION`

#### `DAEMON`

#### `PID`

### `nginx-conf-context`
With the following keys:

#### `SERVER_LOCATION`
#### `SERVER_NAME`
