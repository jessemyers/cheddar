# cheddar

PyPI clone with Flask and Redis

## Features

Cheddar aims to simplify Python development within organizations that work with both private
and public Python distributions.

Cheddar includes:

 -  A *local* package index for internal development, supporting [setuptools][setuptools]'s
    `register` and `upload` commands.
    
 -  A *remote* package index that proxies to a public repository (such as `pypi.python.org`)
    and *caches* packages and release listings locally to reduce latency and minimize the effect
    of downtime byy the public repository.
    
 -  A *combined* package index that combines the best of the local and remote implementations.
 
In addition, Cheddar supports a few features that simplify management within an organization:

 -  Packages are stored locally in separate directories for pre-releases and releases, simplifying
    backup strategies that wish to ignore transitive development builds.
    
 -  Duplicate package uploads return a predictable HTTP `409 Conflict` error.

 -  Mistakenly uploaded packages may be deleted using a simple, RESTful API.

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

 -  A little diagnostic logging would go a long way.
 
 -  Some unit tests using [mockredis][mockredis] would make it easier to manage changes.

 -  A `pip` installation using an extact version match will query a "/simple/{name}/{version}" URL
    before falling back to a general "/simple/{name}" search.
    
    It would be trivial to implement the exact match controller, but it's not clear what response
    `pip` expects in this case.
    
 -  The `setuptools` register command does not send Basic Auth credentials.
 
    It would be much better to password-protect the register controller.
 
 [mockredis]: https://github.com/locationlabs/mockredis
