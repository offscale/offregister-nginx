from sys import version

if version[0] == "2":
    from cStringIO import StringIO

else:
    from io import StringIO

from os import path

from fabric.contrib.files import append, exists
from offregister_fab_utils.apt import apt_depends, get_pretty_name
from offutils import update_d, validate_conf
from pkg_resources import resource_filename

from offregister_nginx import __author__, logger


def install_nginx0(*args, **kwargs):
    apt_depends(c, "apt-transport-https", "ca-certificates", "curl")

    if c.run("dpkg -s nginx", warn=True, hide=True).exited == 0:
        return "nginx is already installed"

    dist = get_pretty_name()
    if (
        c.run(
            "curl -s http://nginx.org/packages/ubuntu/dists/ | grep -sq {dist}".format(
                dist=dist
            ),
            warn=True,
        ).exited
        != 0
    ):
        raise NotImplementedError(
            "nginx official repostories don't support {dist}".format(dist=dist)
        )

    c.run("mkdir -p Downloads")
    key = "nginx_signing.key"
    c.run("curl https://nginx.org/keys/{key} -o Downloads/{key}".format(key=key))
    c.sudo("apt-key add Downloads/{key}".format(key=key))
    append(
        "/etc/apt/sources.list.d/nginx.list",
        (
            lambda endl: (
                "deb {endl}".format(endl=endl),
                "deb-src {endl}".format(endl=endl),
            )
        )(endl="http://nginx.org/packages/ubuntu/ {dist} nginx".format(dist=dist)),
        use_sudo=True,
    )

    apt_depends(c, "nginx")

    return "nginx is now installed"


def setup_nginx_init1(*args, **kwargs):
    if exists(c, runner=c.run, path="/run/systemd/system"):
        if c.run("grep -qF sites-enabled /etc/nginx/nginx.conf", warn=True).exited != 0:
            c.sudo("mkdir -p /etc/nginx/sites-enabled")
            c.sudo(
                "sed -i '$i\  \ \ include /etc/nginx/sites-enabled/*;' /etc/nginx/nginx.conf",
                shell_escape=True,
            )
            c.sudo("systemctl stop nginx", warn=True, hide=True)
            return c.sudo("systemctl start nginx")
        return "nginx already configured for sites-enabled"

    default_conf = {
        "AUTHOR": __author__,
        "DESCRIPTION": "nginx http daemon",
        "DAEMON": "/usr/sbin/nginx",
        "PID": "/var/run/nginx.pid",
    }

    init_name = kwargs.get("nginx-init-name", "nginx.conf")
    init_dir = kwargs.get("nginx-init-dir", "/etc/init")
    init_local_filename = kwargs.get(
        "nginx-upstart-filename",
        resource_filename("offregister_nginx", path.join("conf", "nginx.upstart.conf")),
    )
    service = init_name.partition(".")[0]

    upload_template_fmt(
        c,
        init_local_filename,
        "{init_dir}/{init_name}".format(init_dir=init_dir, init_name=init_name),
        context=update_d(default_conf, kwargs.get("nginx-init-context")),
        use_sudo=True,
    )

    status_cmd = "status {service}".format(service=service)
    if "start/running" in c.run(status_cmd):
        c.sudo("reload {service}".format(service=service))
    else:
        c.sudo("start {service}".format(service=service))
    return c.run(status_cmd)


def setup_nginx_conf2(*args, **kwargs):
    if exists(c, runner=c.run, path="/run/systemd/system"):
        raise NotImplementedError("SystemD not implemented yet")

    init_name = kwargs.get("nginx-init-name", "nginx.conf")
    init_dir = kwargs.get("nginx-init-dir", "/etc/init")
    init_filename = "{init_dir}/{init_name}".format(
        init_dir=init_dir, init_name=init_name
    )
    service = init_name.partition(".")[0]
    status_cmd = "status {service}".format(service=service)
    conf_local_filepath = kwargs.get(
        "nginx-conf-file",
        resource_filename(
            "offregister_nginx", path.join("conf", "nginx.proxy_pass.conf")
        ),
    )
    conf_remote_filename = "/etc/nginx/sites-enabled/{}".format(
        kwargs.get("nginx-conf-filename", path.basename(conf_local_filepath))
    )

    conf = update_d(
        {
            "SERVER_NAME": "forum.*",
            "ROUTE_BLOCK": "location / { try_files $uri @proxy_to_app; }",
            "exit": "forum_app_server",
            "LISTEN": "",
        },
        kwargs.get("nginx-init-context"),
        **kwargs.get("nginx-conf-context", {})
    )

    required = (
        ("SERVER_LOCATION", "unix:/edx/var/forum/forum.sock"),
        ("SERVER_NAME", "forum.*"),
    )

    validate_conf(conf, required, logger)

    if "LISTEN_PORT" in kwargs.get("nginx-conf-context", {}):
        conf["LISTEN"] = "listen {LISTEN_PORT!d};".format(
            LISTEN_PORT=conf["LISTEN_PORT"]
        )

    if conf["SERVER_LOCATION"].startswith("unix"):
        if not exists(c, runner=c.run, path=conf["SERVER_LOCATION"]):
            raise EnvironmentError(
                "{server_location} doesn't exist".format(
                    server_location=conf["SERVER_LOCATION"]
                )
            )
    # http/https is okay, those can be started asynchronously

    if exists(c, runner=c.run, path=init_filename):
        sio = StringIO()
        c.get(init_filename, sio)
        offset = 0
        for l in sio:
            if "include /etc/nginx/sites-enabled/*;" in l:
                if "#" in l:
                    sio.seek(offset)
                    sio.write(l.replace("#", " "))
                    sio.seek(0)
                    c.put(sio, init_filename, use_sudo=True)
                break
            offset = sio.tell()
    else:
        logger.warn(
            "{init_name} not found in {init_dir}".format(
                init_name=init_name, init_dir=init_dir
            )
        )
        raise NotImplementedError("init conf in a weird place; erring")

    upload_template_fmt(
        c, conf_local_filepath, conf_remote_filename, context=conf, use_sudo=True
    )

    if "start/running" in c.run(status_cmd):
        c.sudo("reload {service}".format(service=service))
    else:
        c.sudo("start {service}".format(service=service))
    return c.run(status_cmd)
