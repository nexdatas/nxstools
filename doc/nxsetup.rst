=======
nxsetup
=======

Description
-----------

The nxsetup is is a command-line setup tool for NeXus servers.  It allows to set NXSDataWriter, NXSConfigServer and NXSRecSelector in Tango environment, restart them or change property names.



Synopsis
--------

.. code:: bash

	  nxsetup -x [-j <jsonsettings>] [<server_class1> <server_class2> ... ]

	  nxsetup -r [<server_class1> <server_class2> ... ]

	  nxsetup -a [<server_class1> <server_class2> ... ]

	  nxsetup -p -n newname -o oldname [<server_class1> <server_class2> ... ]


Options:
  -h, --help            show this help message and exit
  -b BEAMLINE, --beamline=BEAMLINE
                        name of the beamline
  -m MASTERHOST, --masterHost=MASTERHOST
                        the host that stores the Mg
  -u USER, --user=USER  the local user
  -d DBNAME, --database=DBNAME
                        the database name
  -j CSJSON, --csjson=CSJSON
                        JSONSettings for the configuration server, (default:
                        '{"host": "localhost","db": <DBNAME>, "use_unicode":
                        true', "read_default_file": "/home/<USER>/.my.cnf"})
  -x, --execute         setup servers action
  -o OLDNAME, --oldname=OLDNAME
                        old property name
  -n NEWNAME, --newname=NEWNAME
                        new property name
  -r, --restart         restart server(s) action
  -a RECPATH, --add-recorder-path=RECPATH
                        add recorder path
  -p, --move-prop       change property name


Example
-------

.. code:: bash

	  nxsetup -x 

	  nxsetup -a /usr/share/pyshared/sardananxsrecorder 

	  nxsetup -p -n DefaultPreselectedComponents -o DefaultAutomaticComponents NXSRecSelector

	  nxsetup -r MacroServer/haso228k