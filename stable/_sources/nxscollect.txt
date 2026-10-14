=========
nxcollect
=========

Description
-----------

The nxsconfig is  a command-line tool dedicated to collect detector images of external formats into the NeXus master file.  The images to collect should be denoted by postrun fields inside NXcollection groups.


Synopsis
--------

.. code:: bash

	   nxscollect [execute|test] [<options>] <command> <main_nexus_file>

execute               execute the collecting process
test                  exceute the process in test mode without changing any files

Options:
  -h, --help            show this help message and exit
  -c COMPRESSION, --compression=COMPRESSION
                        deflate compression rate from 0 to 9 (default: 2)
  -s, --skip_missing    skip missing files
  -r, --replace_nexus_file
                        if it is set the old file is not copied into a file
                        with .__nxscollect__old__* extension
  --pni                 use pni module as a nexus reader/writer
  --h5py                use h5py module as a nexus reader/writer
  --h5cpp               use h5cpp module as a nexus reader/writer


Example
-------

.. code:: bash

	   nxscollect -x -c1 /tmp/gpfs/raw/scan_234.nxs


