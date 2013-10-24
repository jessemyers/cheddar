# cheddar

PyPI clone with Flask and Redis

## Features

Cheddar supports:

 -  A *local* package index for [setuptools][setuptools] `register` and `upload` commands.
 -  A *remote* package index for proxying to another package index (e.g. to `pypi.python.org`)
 -  A *caching* implementation for proxies packages to reduce latency and minimize the effects
    of outages in the remote index.
 -  A *combined* index that supports both local and remote/cached indexes.

 [setuptools]: http://pythonhosted.org/setuptools/

## Configuration

Cheddar can run in any WSGI container or through the built-in development server. Configuation
comes from the `defaults.py` module and any data found by reading a file pointed to by the
`CHEDDAR_SETTINGS` environment variable.

You may wish to modify the `INDEX_URL` and `REDIS_HOSTNAME` variables, which control where
Cheddar finds remote its remote index and Redis, respectively.

## The Local Index

To use the local index:

 1. Edit your `~/.pypirc` to contain an entry for Cheddar. It should look _something_ like:

        [distutils]
        index-servers =
            pypi
            cheddar
        
        [pypi]
        repository:http://pypi.python.org
        
        [cheddar]
        repository:http://localhost:5000/pypi
        username:myusername
        password:mypassword

    Note that the URL here assume you are running the "development" server.

 2. Add credentials to Redis:
 
        redis-cli set cheddar.user.myusername mypasswod
        
 3. Publish and upload your distribution:
 
        cd /path/to/directory/containing/setup.py
        python setup.py register -r cheddar sdist upload -r cheddar

## The Remote Index

Run `pip` using a custom index url:

    pip install --index-url http://localhost:5000/simple
    
Note that the URL here assume you are running the "development" server.

You can also edit your `~/.pip/pip.conf` to contain the index url automatically:

    [install]
    index-url = http://localhost:5000/simple

## Data

Cheddar saves data in several places:

 -  Local packages are stored in the `LOCAL_CACHE_DIR`
 -  Remote packages may be cached in the `REMOTE_CACHE_DIR`
 -  Remote release listings may be cached in Redis.
 -  User data (for upload authentication) is stored in Redis.
 -  Local package release listings are stored Redis.
 
## TODO

Further work:

 -  Support "/simple/{name}/{version}" exact lookups in indexes. (Performance)
 -  Use logging. (Diagnostics)
 -  Add some tests using [mockredis][mockredis]
 -  Figure out why setuptools "register" doesn't support authentication.
 -  Parse PKG-INFO data on upload to local index for better accuracy.
 
 [mockredis]: https://github.com/locationlabs/mockredis
