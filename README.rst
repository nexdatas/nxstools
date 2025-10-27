Welcome to nxstools's documentation!
====================================


|github workflow|
|docs|
|Pypi Version|
|Python Versions|

.. |github workflow| image:: https://github.com/nexdatas/nxstools/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/nexdatas/nxstools/actions
   :alt:

.. |docs| image:: https://img.shields.io/badge/Documentation-webpages-ADD8E6.svg
   :target: https://nexdatas.github.io/nxstools/index.html
   :alt:

.. |Pypi Version| image:: https://img.shields.io/pypi/v/nxstools.svg
                  :target: https://pypi.python.org/pypi/nxstools
                  :alt:

.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/nxstools.svg
                     :target: https://pypi.python.org/pypi/nxstools/
                     :alt:


Authors: Jan Kotanski

------------
Introduction
------------

Configuration tools for NeXDaTaS Tango Servers consists of the following command-line scripts:

- `nxscollect <https://nexdatas.github.io/nxstools/nxscollect.html>`__ uploads external images into the NeXus/HDF5 file
- `nxsconfig <https://nexdatas.github.io/nxstools/nxsconfig.html>`__ reads NeXus Configuration Server settings
- `nxscreate <https://nexdatas.github.io/nxstools/nxscreate.html>`__ creates NeXus Configuration components
- `nxsdata <https://nexdatas.github.io/nxstools/nxsdata.html>`__ runs NeXus Data Writer
- `nxsfileinfo <https://nexdatas.github.io/nxstools/nxsfileinfo.html>`__ shows metadata of the NeXus/HDF5 file
- `nxsetup <https://nexdatas.github.io/nxstools/nxsetup.html>`__ setups NeXDaTaS Tango Server environment

as well as the `nxstools <https://nexdatas.github.io/nxstools/nxstools.html>`__ package which allows perform these operations
directly from a python code.

| Source code: https://github.com/nexdatas/nxstools
| Web page: https://nexdatas.github.io/nxstools
| NexDaTaS Web page: https://nexdatas.github.io

------------
Installation
------------

Install the dependencies:

|    pninexus or h5py, numpy, tango, sphinx

From sources
""""""""""""

Download the latest NXS Tools version from

|    https://github.com/nexdatas/nxstools

Extract sources and run

.. code-block:: console

	  $ python3 setup.py install

Debian packages
"""""""""""""""

Debian `trixie`, `bookworm`, `bullseye`  or Ubuntu `questing`, `noble`, `jammy` packages can be found in the HDRI repository.

To install the debian packages, add the PGP repository key

.. code-block:: console

	  $ sudo su
	  $ curl -s http://repos.pni-hdri.de/debian_repo.pub.gpg | gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/debian-hdri-repo.gpg --import
	  $ chmod 644 /etc/apt/trusted.gpg.d/debian-hdri-repo.gpg

and then download the corresponding source list

.. code-block:: console

	  $ cd /etc/apt/sources.list.d
	  $ wget http://repos.pni-hdri.de/trixie-pni-hdri.sources

To install nxstools scripts

.. code-block:: console

	  $ apt-get update
	  $ apt-get install nxstools

or

.. code-block:: console

	  $ apt-get update
	  $ apt-get install nxstools3

for older python3 releases.

To install only the python3 package

.. code-block:: console

	  $ apt-get update
	  $ apt-get install python3-nxstools

and for python2

.. code-block:: console

	  $ apt-get update
	  $ apt-get install python-nxstools

if exists.


From pip
""""""""

To install it from pip you can

.. code-block:: console

   $ python3 -m venv myvenv
   $ . myvenv/bin/activate

   $ pip install nxstools

Moreover it is also good to install

.. code-block:: console

   $ pip install pytango
