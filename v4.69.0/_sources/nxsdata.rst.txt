=======
nxsdata
=======

Description
-----------

The nxsdata program is a command-line interface to Nexus Data Tango Server.
Program allows one to store NeXuS Data in H5 files.
The writer provides storing data from other Tango devices, various databases
as well as passed by a user client via JSON strings.


Synopsis
--------

.. code:: bash

	  nxsdata <command> [-s <nexus_server>]  [<arg1> [<arg2>  ...]]

Commands:
   openfile [-s <nexus_server>]  <file_name>
          open new H5 file
   setdata [-s <nexus_server>] <json_data_string>
          assign global JSON data
   openentry [-s <nexus_server>] <xml_config>
          create new entry
   record [-s <nexus_server>]  <json_data_string>
          record one step with step JSON data
   closeentry [-s <nexus_server>]
          close the current entry
   closefile [-s <nexus_server>]
          close the current file
   servers [-s <nexus_server/host>]
          get lists of tango data servers from the current tango host


Options:
  -h, --help            show this help message and exit
  -s SERVER, --server=SERVER
                        tango data server device name


Example
-------

.. code:: bash

	  nxsdata openfile -s p02/tangodataserver/exp.01  /user/data/myfile.h5

