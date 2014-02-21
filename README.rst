=======
cheddar
=======

.. image:: https://badge.fury.io/py/cheddar.png
    :target: http://badge.fury.io/py/cheddar

.. image:: https://travis-ci.org/jessemyers/cheddar.png?branch=develop
        :target: https://travis-ci.org/jessemyers/cheddar

.. image:: https://pypip.in/d/cheddar/badge.png
        :target: https://crate.io/packages/cheddar?version=latest


PyPI clone with Flask and Redis. It's the single most popular cheese in the world!

* Free software: Apache License V2
* Documentation: http://cheddar.rtfd.org.

Features
--------

Cheddar aims to simplify Python development within organizations that simultaneously work
with public and private Python distributions.

Cheddar includes:

* A *local* package index for internal development, supporting `setuptools`_ ``register`` and ``upload`` commands.

* A *remote* package index that proxies to a public repository (such as ``pypi.python.org``)
  and *caches* packages and package version listings to reduce latency and minimize the effect
  of downtime by the public repository.

* A *combined* package index that unifies the best of the local and remote implementations.
 
In addition, Cheddar supports a few features that simplify management within an organization:

* Packages are stored locally in separate directories for pre-releases and releases, simplifying
  backup strategies that wish to ignore transitive development builds.
    
* Duplicate package uploads return a predictable HTTP `409 Conflict` error.

* Mistakenly uploaded packages may be deleted using a simple, RESTful API.

Configuration
-------------

Cheddar can run in any WSGI container or through Flask's built-in development server (which is
single-threaded and only recommended for development).

Configuation is loaded from the ``defaults.py`` module along with the contents of the file pointed
to by the ``CHEDDAR_SETTINGS`` environment variable, if any.

You may wish to modify several of the configuration parameters from their default values, including:

* `INDEX_URL` which specifies the URL of the *remote* package index
* `REDIS_HOSTNAME` which control the location of the Redis server
* `LOCAL_CACHE_DIR` which controls the storage location of locally uploaded files
* `REMOTE_CACHE_DIR` which controls the storage location of cached remote files

The Local Index
---------------

To use the local index:

 1. Edit your ``~/.pypirc`` to contain an entry for Cheddar. It should look _something_ like::

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

    Note that the URL here assumes you are running the "development" server.

 2. Add credentials to Redis::
 
        redis-cli set cheddar.user.myusername mypassword
        
 3. Upload your distribution::
 
        cd /path/to/directory/containing/setup.py
        python setup.py sdist upload -r cheddar

    You may also use the ``register -r cheddar`` to validate your ``setup.py`` without
    uploading the source distribution.

The Remote Index
----------------

Run `pip` using a custom index url::

    pip install --index-url http://localhost:5000/simple
    
Note that the URL here assumes you are running the "development" server.

You can also edit your ``~/.pip/pip.conf`` to contain the index url automatically::

    [install]
    index-url = http://localhost:5000/simple

Data
----

Cheddar saves data in several places:

* Local packages are stored in the `LOCAL_CACHE_DIR`
* Remote packages may be cached in the `REMOTE_CACHE_DIR`
* Remote version listings may be cached in Redis.
* User data (for upload authentication) is stored in Redis.
* Local package version listings are stored Redis.


.. _`setuptools`: http://pythonhosted.org/setuptools/
