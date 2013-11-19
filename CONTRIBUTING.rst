============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given. 

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/jessemyers/cheddar/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

cheddar could always use more documentation, whether as part of the 
official cheddar docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/jessemyers/cheddar/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `cheddar` for local development.

1. Fork the `cheddar` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/cheddar.git

3. Install your local copy into a virtualenv. this is how you set up your fork for local development::

    $ virtualenv venv
    $ source venv/bin/activate
    $ python setup.py develop

4. Create a branch for local development::

    $ git flow feature start name-of-your-bugfix-or-feature

  Now you can make your changes locally.

5. When you're done making changes, check that your changes pass flake8 and the
tests, including testing other Python versions with tox::

    $ flake8 cheddar tests
	  $ python setup.py test
    $ tox

  To get flake8 and tox, just pip install them into your virtualenv. 

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git flow feature finish name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

Cheddar uses `gitflow`_ for its branch management.

1. Implement changes in new git branches, following git-flow's model:
 
 * Changes based off of *develop* will receive the least amount of skepticism.
       
 * Changes based off of a *release* branches (if one exists) will be considered,
   especially for small bug fixes relevant to the release. We are not likely to 
   accept new features against *release* branches.
       
 * Changes based off of *master* or a prior release tag will be given the most 
   skepticism. We may accept patches for major bugs against past releases, but
   would prefer to see such changes follow the normal git-flow process.
       
    We will not accept new features based off of *master*.

2. Limit the scope of changes to a single bug fix or feature per branch.
 
3. Treat documentation and unit tests as an essential part of any change.
 
4. Update the change log appropriately.

5. The pull request should work for Python 2.7 and PyPy Check
   https://travis-ci.org/jessemyers/cheddar/pull_requests
   and make sure that the tests pass for all supported Python versions.

.. _`gitflow`: https://github.com/nvie/gitflow