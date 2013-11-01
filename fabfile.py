from os.path import dirname

from fabric.api import env, put, sudo, task

env.use_ssh_config = True

PACKAGES = [
    "nginx",
    "python2.7",
    "python-setuptools",
    "python-dev",
    "build-essential",
    "supervisor",
    "redis-server",
]

DIRECTORIES = [
    ("/etc/cheddar", None),
    ("/usr/lib/cheddar", None),
    ("/usr/share/cheddar", "nobody"),
    ("/var/log/cheddar", "nobody"),
    ("/var/run/cheddar", "nobody"),
]

FILES = [
    "/etc/cheddar/cheddar.conf",
    "/etc/nginx/sites-available/cheddar",
    "/etc/cheddar/uwsgi.ini",
    "/etc/supervisor/conf.d/cheddar.conf",
]


@task
def install_packages():
    for package in PACKAGES:
        sudo("apt-get install {} -y -q".format(package))


@task
def uninstall_packages():
    for package in PACKAGES:
        sudo("apt-get remove --purge -y -q {}".format(package))
    sudo("apt-get autoremove -y -q")


@task
def create_directories():
    for directory, owner in DIRECTORIES:
        sudo("mkdir -p {}".format(directory))
        if owner is not None:
            sudo("chown {} {}".format(owner, directory))


@task
def remove_directories():
    for directory, owner in DIRECTORIES:
        sudo("rm -rf {}".format(directory))


@task
def create_files():
    for file_ in FILES:
        put("{}/conf{}".format(dirname(__file__), file_), file_, use_sudo=True)


@task
def remove_files():
    for file_ in FILES:
        sudo("rm -f {}".format(file_))


@task
def create_virtualenv():
    sudo("easy_install pip")
    sudo("pip install virtualenv")
    sudo("virtualenv /usr/lib/cheddar/venv")
    sudo("/usr/lib/cheddar/venv/bin/pip install -q git+https://github.com/jessemyers/cheddar.git@release/1.0#egg=cheddar")  # noqa
    sudo("/usr/lib/cheddar/venv/bin/pip install -q 'uwsgi>=1.9.18.2'")


@task
def remove_virtualenv():
    sudo("rm -rf /usr/lib/cheddar/venv")


@task
def enable():
    sudo("supervisorctl reload")
    sudo("rm -f /etc/nginx/sites-enabled/default")
    sudo("ln -sf ../sites-available/cheddar /etc/nginx/sites-enabled/")
    if sudo("service nginx status", warn_only=True):
        sudo("service nginx start")
    else:
        sudo("service nginx reload")


@task
def disable():
    sudo("rm -f /etc/nginx/sites-enabled/cheddar")
    sudo("ln -sf ../sites-available/default /etc/nginx/sites-enabled/")
    if sudo("service nginx status", warn_only=True):
        sudo("service nginx start")
    else:
        sudo("service nginx reload")
    sudo("supervisorctl stop cheddar")


@task
def uninstall():
    disable()
    remove_files()
    remove_directories()
    uninstall_packages()


@task
def install():
    install_packages()
    create_directories()
    create_files()
    create_virtualenv()
    enable()
