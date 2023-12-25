Install
=======
| Installation for this project is somewhat complicated, so try to follow the recommended details to achieve the easiest installation process.


| Operating System:
-----------------------

| * Windows and Linux are much easier to complete this process on
| * Mac OS is more problematic, yet possible and many users have completed this process successfully.
| * If you still have issues, consider using docker. dockerfiles are provided.


| Python Version:
-------------------------


| * Stable version for this project is 3.6
| * Starting on v1.6.0 python 3.7 is also supported, but it's not stable yet. So difficulties may occur. Your best best is using 3.6.
|
| Linux and Windows Installations are automatically tested using github actions. Mac OS users might have an issue with Bcolz.
|  Users have found that the easiest way to get Bcolz installed is using conda like so:

  .. code-block:: bash

     conda install -c conda-forge bcolz

| If you use Python for anything other than Zipline, I **strongly** recommend
  that you install in a `virtualenv <https://virtualenv.readthedocs.org/en/latest>`_.

| When using postgres, some users had difficulties installing ``psyccopg2``. A workaround is installing it manually prior to zt

.. code-block:: bash

    conda install -c conda-forge psycopg2=2.8.6

The `Hitchhiker's Guide to Python`_ provides an `excellent tutorial on virtualenv
<https://docs.python-guide.org/en/latest/dev/virtualenvs/>`_.

Installation Tutorial
------------------------

.. raw:: html

    <iframe width="660" height="315" src="https://www.youtube.com/embed/gsUnCjl5mrg" frameborder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen></iframe>


Installing with git clone
--------------------------
Installing the cutting edge version, directly from the master branch. Just remember that documentation is not always up to date with latest and greatest.
Using the Master branch install is for the more advanced users.
 * git clone https://github.com/gwhk/zipline-trader.git
 * <create/activate a virtual env> - optional but recommended
 * python -m pip install --upgrade pip
 * pip install -e .

Installing using pip directly from github
----------------------------------------------
You can install it with ability to debug it like this:

.. code-block:: bash

    python -m pip install --upgrade pip
    pip install -e git://github.com/gwhk/zipline-trader.git#egg=zipline-trader

To install a specific version, you could do this (installing version 1.6.0):

.. code-block:: bash

    python -m pip install --upgrade pip
    pip install -e git://github.com/gwhk/zipline-trader.git@1.6.0#egg=zipline-trader


The last step will install this project from source, giving you the ability to debug zipline-trader's code.

Installing from pypi
---------------------
The stable version is available on pypi (currently 1.6.0).


Installing from Anaconda
---------------------------
* Installing using Anaconda is not supported.


Notes
----------

Installing zipline is a bit complicated, and therefore installing zipline-trader.
There are two reasons for zipline installation additional complexity:

1. Zipline ships several C extensions that require access to the CPython C API.
   In order to build the C extensions, ``pip`` needs access to the CPython
   header files for your Python installation.

2. Zipline depends on `numpy <https://www.numpy.org/>`_, the core library for
   numerical array computing in Python.  Numpy depends on having the `LAPACK
   <https://www.netlib.org/lapack>`_ linear algebra routines available.

Because LAPACK and the CPython headers are non-Python dependencies, the correct
way to install them varies from platform to platform.
Once you've installed the necessary additional dependencies (see below for
your particular platform)

GNU/Linux
))))))))))))))))

On `Debian-derived`_ Linux distributions, you can acquire all the necessary
binary dependencies from ``apt`` by running:

.. code-block:: bash

   $ sudo apt-get install libatlas-base-dev python-dev gfortran pkg-config libfreetype6-dev hdf5-tools

On recent `RHEL-derived`_ derived Linux distributions (e.g. Fedora), the
following should be sufficient to acquire the necessary additional
dependencies:

.. code-block:: bash

   $ sudo dnf install atlas-devel gcc-c++ gcc-gfortran libgfortran python-devel redhat-rpm-config hdf5

On `Arch Linux`_, you can acquire the additional dependencies via ``pacman``:

.. code-block:: bash

   $ pacman -S lapack gcc gcc-fortran pkg-config hdf5

There are also AUR packages available for installing `ta-lib
<https://aur.archlinux.org/packages/ta-lib/>`_, an optional Zipline dependency.

OSX
))))))))))

The version of Python shipped with OSX by default is generally out of date, and
has a number of quirks because it's used directly by the operating system.  For
these reasons, many developers choose to install and use a separate Python
installation. The `Hitchhiker's Guide to Python`_ provides an excellent guide
to `Installing Python on OSX <https://docs.python-guide.org/en/latest/>`_, which
explains how to install Python with the `Homebrew`_ manager.

Assuming you've installed Python with Homebrew, you'll also likely need the
following brew packages:

.. code-block:: bash

   $ brew install freetype pkg-config gcc openssl hdf5

..

.. _`Debian-derived`: https://www.debian.org/misc/children-distros
.. _`RHEL-derived`: https://en.wikipedia.org/wiki/Red_Hat_Enterprise_Linux_derivatives
.. _`Arch Linux` : https://www.archlinux.org/
.. _`Hitchhiker's Guide to Python` : http://docs.python-guide.org/en/latest/
.. _`Homebrew` : http://brew.sh

