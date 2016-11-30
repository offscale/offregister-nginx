from cStringIO import StringIO
from os import path

from offutils import update_d, validate_conf
from pkg_resources import resource_filename

from fabric.operations import sudo, run, put, get
from fabric.contrib.files import append, upload_template, exists

from offregister_fab_utils.apt import apt_depends, get_pretty_name

from offregister_nginx import __author__, logger


def install_nginx0(*args, **kwargs):
    apt_depends('apt-transport-https', 'ca-certificates', 'curl')

    dist = get_pretty_name()
    if run('curl -s http://nginx.org/packages/ubuntu/dists/ | grep -sq {dist}'.format(dist=dist),
           warn_only=True).failed:
        raise NotImplementedError("nginx official repostories don't support {dist}".format(dist=dist))

    run('mkdir -p Downloads')
    key = 'nginx_signing.key'
    run('curl https://nginx.org/keys/{key} -o Downloads/{key}'.format(key=key))
    sudo('apt-key add Downloads/{key}'.format(key=key))
    append('/etc/apt/sources.list.d/nginx.list',
           (lambda endl: ('deb {endl}'.format(endl=endl), 'deb-src {endl}'.format(endl=endl)))(
               endl='http://nginx.org/packages/ubuntu/ {dist} nginx'.format(dist=dist)), use_sudo=True)

    apt_depends('nginx')


def setup_nginx_init1(*args, **kwargs):
    if exists('/run/systemd/system'):
        raise NotImplementedError('SystemD not implemented yet')

    default_conf = {
        'AUTHOR': __author__,
        'DESCRIPTION': 'nginx http daemon',
        'DAEMON': '/usr/sbin/nginx',
        'PID': '/var/run/nginx.pid'
    }

    init_name = kwargs.get('nginx-init-name', 'nginx.conf')
    init_dir = kwargs.get('nginx-init-dir', '/etc/init')
    init_local_filename = kwargs.get('nginx-upstart-filename',
                                     resource_filename('offregister_nginx', path.join('conf', 'nginx.upstart.conf')))
    service = init_name.partition('.')[0]

    upload_template(init_local_filename, '{init_dir}/{init_name}'.format(init_dir=init_dir, init_name=init_name),
                    context=update_d(default_conf, kwargs.get('nginx-init-context')), use_sudo=True)

    status_cmd = 'status {service}'.format(service=service)
    if 'start/running' in run(status_cmd):
        sudo('reload {service}'.format(service=service))
    else:
        sudo('start {service}'.format(service=service))
    return run(status_cmd)


def setup_nginx_conf2(*args, **kwargs):
    init_name = kwargs.get('nginx-init-name', 'nginx.conf')
    init_dir = kwargs.get('nginx-init-dir', '/etc/init')
    init_filename = '{init_dir}/{init_name}'.format(init_dir=init_dir, init_name=init_name)
    service = init_name.partition('.')[0]
    status_cmd = 'status {service}'.format(service=service)
    conf_local_filepath = kwargs.get('nginx-conf-file',
                                     resource_filename('offregister_nginx', path.join('conf', 'nginx.proxy_pass.conf')))
    conf_remote_filename = '/etc/nginx/sites-enabled/{}'.format(
        kwargs.get('nginx-conf-filename', path.basename(conf_local_filepath))
    )

    conf = update_d({
        'SERVER_NAME': 'forum.*',
        'ROUTE_BLOCK': 'location / { try_files $uri @proxy_to_app; }',
        'exit': 'forum_app_server',
        'LISTEN': ''
    }, kwargs.get('nginx-init-context'), **kwargs.get('nginx-conf-context', {}))

    required = (
        ('SERVER_LOCATION', 'unix:/edx/var/forum/forum.sock'),
        ('SERVER_NAME', 'forum.*')
    )

    validate_conf(conf, required, logger)

    if 'LISTEN_PORT' in kwargs.get('nginx-conf-context', {}):
        conf['LISTEN'] = 'listen {LISTEN_PORT!d};'.format(LISTEN_PORT=conf['LISTEN_PORT'])

    if conf['SERVER_LOCATION'].startswith('unix'):
        if not exists(conf['SERVER_LOCATION']):
            raise EnvironmentError("{server_location} doesn't exist".format(server_location=conf['SERVER_LOCATION']))
    # http/https is okay, those can be started asynchronously

    if exists(init_filename):
        sio = StringIO()
        get(init_filename, sio)
        offset = 0
        for l in sio:
            if 'include /etc/nginx/sites-enabled/*;' in l:
                if '#' in l:
                    sio.seek(offset)
                    sio.write(l.replace('#', ' '))
                    sio.seek(0)
                    put(sio, init_filename, use_sudo=True)
                break
            offset = sio.tell()
    else:
        logger.warn('{init_name} not found in {init_dir}'.format(init_name=init_name, init_dir=init_dir))
        raise NotImplementedError('init conf in a weird place; erring')

    upload_template(conf_local_filepath, conf_remote_filename, context=conf, use_sudo=True)

    if 'start/running' in run(status_cmd):
        sudo('reload {service}'.format(service=service))
    else:
        sudo('start {service}'.format(service=service))
    return run(status_cmd)
