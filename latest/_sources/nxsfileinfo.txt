===========
nxsfileinfo
===========

Description
-----------

The nxsfileinfo program show metadata from nexus files

Synopsis
--------

.. code:: bash

	  nxsfileinfo <command> [options] <nexus_file_name>


The following commands are available: general, field


nxsfileinfo general
-------------------

It shows general information for he nexus file.

Synopsis
""""""""

.. code:: bash

	  nxsfileinfo general <nexus_file_name>

Options:
  -h, --help            show this help message and exit
  --pni                 use pni module as a nexus reader
  --h5py                use h5py module as a nexus reader
  --h5cpp               use h5cpp module as a nexus reader

Example
"""""""

.. code:: bash

	  nxsfileinfo general saxs_ref1_02.nxs

nxsfileinfo field
-----------------

It shows field information for the nexus file.

Synopsis
""""""""

.. code:: bash

	  Usage: nxsfileinfo field <file_name>

Options:
   -h, --help            show this help message and exit
   -c HEADERS, --columns=HEADERS
       names of column to be shown (separated by commas without spaces). The possible names are: depends_on, dtype, full_path, nexus_path, nexus_type, shape, source, source_name, source_type, strategy, trans_type, trans_offset, trans_vector, units, value
   -f FILTERS, --filters=FILTERS
       full_path filters (separated by commas without spaces). Default: '*'. E.g. '*:NXsample/*'
   -v VALUES, --values=VALUES
       field names which value should be stored (separated by commas without spaces). Default: depends_on
   -g, --geometry        show fields with geometry full_path filters, i.e. *:NXtransformations/*,*/depends_on. It works only when -f is not defined
   -s, --source          show datasource parameters
   --pni                 use pni module as a nexus reader
   --h5py                use h5py module as a nexus reader

Example
"""""""

.. code:: bash

	  nxsfileinfo field /tmp/saxs_ref1_02.nxs
