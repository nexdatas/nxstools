=======
nxsetup
=======

Description
-----------

The nxsetup is is a command-line setup tool for NeXus servers.  It allows to set NXSDataWriter, NXSConfigServer and NXSRecSelector in Tango environment, restart them or change property names.

Synopsis
--------

.. code:: bash

	  nxscreate  <command> [ <options>]  [<arg1> [<arg2>  ...]]


The following commands are available: set, restart, start, stop, move-prop, change-prop, add-recorder-path


nxsetup set
-----------

.. code:: bash

    usage: nxsetup set [-h] [-b BEAMLINE] [-m MASTERHOST] [-u USER] [-d DBNAME]
		       [-j CSJSON]
		       [server_name [server_name ...]]

    set up NXSConfigServer NXSDataWriter and NXSRecSelector servers

    positional arguments:
      server_name           server names, e.g.: NXSRecSelector NXSDataWriter/TDW1

    optional arguments:
      -h, --help            show this help message and exit
      -b BEAMLINE, --beamline BEAMLINE
			    name of the beamline ( default: 'nxs' )
      -m MASTERHOST, --masterHost MASTERHOST
			    the host that stores the Mg ( default: <localhost> )
      -u USER, --user USER  the local user ( default: 'tango' )
      -d DBNAME, --database DBNAME
			    the database name ( default: 'nxsconfig')
      -j CSJSON, --csjson CSJSON
			    JSONSettings for the configuration server. ( default:
			    '{"host": "localhost","db": <DBNAME>, "use_unicode":
			    true', "read_default_file": <MY_CNF_FILE>}' where
			    <MY_CNF_FILE> stays for "/home/<USER>/.my.cnf" or
			    "/var/lib/nxsconfigserver/.my.cnf" )

     examples:
	   nxsetup set
	   nxsetup set -b p09 -m haso228 -u p09user -d nxsconfig NXSConfigServer


nxsetup restart
---------------

.. code:: bash

    usage: nxsetup restart [-h] [-l LEVEL] [server_name [server_name ...]]

    restart tango server

    positional arguments:
      server_name           server names, e.g.: NXSRecSelector NXSDataWriter/TDW1

    optional arguments:
      -h, --help            show this help message and exit
      -l LEVEL, --level LEVEL
			    startup level

     examples:
	   nxsetup restart Pool/haso228 -l 2


nxsetup start
-------------

.. code:: bash

    usage: nxsetup start [-h] [-l LEVEL] [server_name [server_name ...]]

    start tango server

    positional arguments:
      server_name           server names, e.g.: NXSRecSelector NXSDataWriter/TDW1

    optional arguments:
      -h, --help            show this help message and exit
      -l LEVEL, --level LEVEL
			    startup level

     examples:
	   nxsetup start Pool/haso228 -l 2

nxsetup stop
------------

.. code:: bash

    usage: nxsetup stop [-h] [server_name [server_name ...]]

    stop tango server

    positional arguments:
      server_name           server names, e.g.: NXSRecSelector NXSDataWriter/TDW1

    optional arguments:
      -h, --help            show this help message and exit

     examples:
	   nxsetup stop Pool/haso228


nxsetup move-prop
-----------------

.. code:: bash

    usage: nxsetup move-prop [-h] [-n NEWNAME] [-o OLDNAME]
			     [server_name [server_name ...]]

    change property name

    positional arguments:
      server_name           server names, e.g.: NXSRecSelector NXSDataWriter/TDW1

    optional arguments:
      -h, --help            show this help message and exit
      -n NEWNAME, --newname NEWNAME
			    (new) property name
      -o OLDNAME, --oldname OLDNAME
			    old property name
      -t, --postpone        do not restart the server
    
     examples:
	   nxsetup move-prop -n DefaultPreselectedComponents -o DefaultAutomaticComponents NXSRecSelector
           nxsetup move-prop -t -n DefaultPreselectedComponents  -o DefaultAutomaticComponents NXSRecSelector


nxsetup change-prop
-------------------

.. code:: bash

    usage: nxsetup change-prop [-h] [-n NEWNAME] [-w PROPVALUE]
			       [server_name [server_name ...]]

    change property value

    positional arguments:
      server_name           server names, e.g.: NXSRecSelector NXSDataWriter/TDW1

    optional arguments:
      -h, --help            show this help message and exit
      -n NEWNAME, --newname NEWNAME
			    (new) property name
      -w PROPVALUE, --propvalue PROPVALUE
			    new property value
      -t, --postpone        do not restart the server
    

     examples:
           nxsetup change-prop -n ClientRecordKeys -t -w "[\"phoibos_scan_command\",\"phoibos_scan_comment\"]" NXSRecSelector/r228
	   nxsetup change-prop -n DefaultPreselectedComponents -w "[\"pinhole1\",\"slit2\"]" NXSRecSelector/r228
           nxsetup change-prop -n StartDsPath -w "[\"/usr/bin\",\"/usr/lib/tango\"]" Starter

nxsetup add-recorder-path
-------------------------

.. code:: bash

    usage: nxsetup add-recorder-path [-h] recorder_path

    add-recorder-path into MacroServer(s) property

    positional arguments:
      recorder_path  sardana recorder path

    optional arguments:
      -h, --help     show this help message and exit
      -t, --postpone  do not restart the server
     examples:
	   nxsetup add-recorder-path /usr/share/pyshared/sardananxsrecorder
	   nxsetup add-recorder-path -t /usr/share/pyshared/sardananxsrecorder
