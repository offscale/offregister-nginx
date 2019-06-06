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
## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or <https://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or <https://opensource.org/licenses/MIT>)

at your option.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in the work by you, as defined in the Apache-2.0 license, shall be
dual licensed as above, without any additional terms or conditions.