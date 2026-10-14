=========
nxscreate
=========

Description
-----------

The nxscreate program allows one to create simple datasources and components.

Synopsis
--------

.. code:: bash

	  nxscreate  <command> [ <options>]  [<arg1> [<arg2>  ...]]


The following commands are available: clientds, tangods, deviceds, onlineds, onlinecp, comp.


nxscreate clientds
------------------

It creates a set of CLIENT datasources.

Synopsis
""""""""

.. code:: bash

	  nxscreate clientds [options] [name1] [name2]

- with -b: datasources are created in Configuration Server database
- without -b: datasources are created on the local filesystem in -d <directory>
- default <directory> is '.'
- default <server> is taken from Tango DB


Options:
  -h, --help            show this help message and exit
  -v DEVICE, --device-prefix=DEVICE
                        device prefix, i.e. exp_c (mandatory w/o <name1>)
  -f FIRST, --first=FIRST
                        first index (mandatory w/o <name1>)
  -l LAST, --last=LAST  last index (mandatory w/o <name1>)
  -o, --overwrite       overwrite existing datasources
  -d DIRECTORY, --directory=DIRECTORY
                        output datasource directory
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -s DSOURCE, --datasource-prefix=DSOURCE
                        datasource prefix, i.e. counter (useful for avoiding duplicated datasource names)
  -b, --database        store datasources in Configuration Server database
  -m, --minimal_device  device name without first '0'
  -r SERVER, --server=SERVER
                        configuration server device name

Example
"""""""

.. code:: bash

	   nxscreate clientds starttime -b
	   nxscreate clientds title -d /home/user/xmldir
	   nxscreate clientds -v exp_c -f1 -l4 -b
	   nxscreate clientds -v hasppXX:10000/expchan/vfcadc_exp/ -f1 -l8  -m -b -s exp_vfc

nxscreate tangods
-----------------

It creates a set of TANGO datasources.

Synopsis
""""""""

.. code:: bash

	  nxscreate tangods [options]

- with -b: datasources are created in Configuration Server database
- without -b: datasources are created on the local filesystem in -d <directory>
- default <directory> is '.'
- default <server> is taken from Tango DB
- default <datasource> is 'exp_mot'
- default <host>, <port> are taken from <server>

Options:
  -h, --help            show this help message and exit
  -v DEVICE, --device-prefix=DEVICE
                        device prefix, i.e. exp_c (mandatory)
  -f FIRST, --first=FIRST
                        first index
  -l LAST, --last=LAST  last index
  -a ATTRIBUTE, --attribute=ATTRIBUTE
                        tango attribute name
  -s DATASOURCE, --datasource-prefix=DATASOURCE
                        datasource-prefix (useful for avoiding duplicated
                        datasource names)
  -o, --overwrite       overwrite existing datasources
  -d DIRECTORY, --directory=DIRECTORY
                        output datasource directory
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -u HOST, --host=HOST  tango host name
  -t PORT, --port=PORT  tango host port
  -b, --database        store datasources in Configuration Server database
  -g GROUP, --group=GROUP
                        device group name
  -e ELEMENTTYPE, --elementtype=ELEMENTTYPE
                        element type, i.e. attribute, property or command
  -r SERVER, --server=SERVER
                        configuration server device name

Example
"""""""

.. code:: bash

	   nxscreate tangods -f1 -l2  -v p09/motor/exp. -s exp_mot
	   nxscreate tangods -f1 -l32  -v p02/motor/eh1a. -s exp_mot -b
	   nxscreate tangods -f1 -l32  -v p01/motor/oh1. -s exp_mot -b
           nxscreate tangods -f1 -l8  -v pXX/slt/exp. -s slt_exp_ -u hasppXX.desy.de -b
           nxscreate tangods -v petra/globals/keyword -s source_current -u haso228 -t 10000 \ 
                             -a BeamCurrent -b -r p09/nxsconfigserver/haso228 -o -g __CLIENT__


nxscreate deviceds
------------------

It creates a set of TANGO datasources for all device attributes.

Synopsis
""""""""

.. code:: bash

	  nxscreate deviceds [options] [dv_attr1 [dv_attr2 [dv_attr3 ...]]]

- without <dv_attr1>: datasources for all attributes are created
- with -b: datasources are created in Configuration Server database
- without -b: datasources are created on the local filesystem in -d <directory>
- default <directory> is '.'
- default <server> is taken from Tango DB
- default <datasource> is 'exp_mot'
- default <host>, <port> are taken from <server>

Options:
  -h, --help            show this help message and exit
  -v DEVICE, --device=DEVICE
                        device, i.e. p09/pilatus300k/01 (mandatory)
  -o DATASOURCE, --datasource-prefix=DATASOURCE
                        datasource-prefix
  -d DIRECTORY, --directory=DIRECTORY
                        output datasource directory
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -s HOST, --host=HOST  tango host name
  -t PORT, --port=PORT  tango host port
  -b, --database        store datasources in Configuration Server database
  -n, --no-group        don't create common group with a name of datasource
                        prefix
  -r SERVER, --server=SERVER
                        configuration server device name

Example
"""""""

.. code:: bash

	   nxscreate deviceds  -v p09/pilatus/haso228k
	   nxscreate deviceds  -v p09/lambda2m/haso228k  -s haslambda -b
	   nxscreate deviceds  -v p09/pilatus300k/haso228k -b -o pilatus300k_ RoI Energy ExposureTime


nxscreate onlineds
------------------

It creates a set of motor datasources from an online xml file.

Synopsis
""""""""

.. code:: bash

	  nxscreate onlineds [options] inputFile

- with -b: datasources are created in Configuration Server database
- with -d <directory>: datasources are created on the local filesystem
- without -b or -d <directory>: run in the test mode
- default <inputFile> is '/online_dir/online.xml'
- default <server> is taken from Tango DB

`onlineds` overwrites existing datasources

Options:
  -h, --help            show this help message and exit
  -b, --database        store components in Configuration Server database
  -t, --noclientlike    set motor tango datasources to be non __CLIENT__ like
  -d DIRECTORY, --directory=DIRECTORY
                        output directory where datasources will be saved
  -n, --nolower         do not change aliases into lower case
  -r SERVER, --server=SERVER
                        configuration server device name
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -e EXTERNAL, --external=EXTERNAL
                        external configuration server
  -p XMLPACKAGE, --xml-package=XMLPACKAGE
                        xml template package
  --verbose             printout verbose mode
			
Example
"""""""

.. code:: bash

	   nxscreate onlineds -b
	   nxscreate onlineds -b -t
	   nxscreate onlineds -d /home/user/xmldir
	   nxscreate onlineds


nxscreate poolds
----------------

It creates a set of motor datasources from a sardana pool device channels.

Synopsis
""""""""

.. code:: bash

	  nxscreate onlineds [options] [channel [channel]]

- with -b: datasources are created in Configuration Server database
- with -d <directory>: datasources are created on the local filesystem
- without -b or -d <directory>: run in the test mode
- default <channel> is 'ALL'
- default <server> is taken from Tango DB
- default <pool> is taken from Tango DB

`poolds` overwrites existing datasources

Options:
  -h, --help            show this help message and exit
  -b, --database        store components in Configuration Server database
  -t, --noclientlike    set motor tango datasources to be non __CLIENT__ like
  -d DIRECTORY, --directory=DIRECTORY
                        output directory where datasources will be saved
  -n, --nolower         do not change aliases into lower case
  -r SERVER, --server=SERVER
                        configuration server device name
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -p POOL, --pool=POOL
                        sardana pool device name

Example
"""""""

.. code:: bash

           nxscreate poolds -b  
           nxscreate poolds -b -t 
           nxscreate poolds -d -s p09/pool/haso228 
           nxscreate poolds -b Motor CTExpChannel 
           nxscreate poolds -b mot01 mot03 
           nxscreate poolds


nxscreate onlinecp
------------------

It creates a detector component from the online.xml file
and its set of datasources.

Synopsis
""""""""

.. code:: bash

	  nxscreate onlinecp [options] inputFile

- without '-c <component>': show a list of possible components
- with -b: datasources are created in Configuration Server database
- without -b: datasources are created on the local filesystem in -d <directory>
- default <directory> is '.'
- default <inputFile> is '/online_dir/online.xml'
- default <server> is taken from Tango DB


Options:
  -h, --help            show this help message and exit
  -c COMPONENT, --component=COMPONENT
                        component namerelated to the device name from
                        <inputFile>
  -r SERVER, --server=SERVER
                        configuration server device name
  -n, --nolower         do not change aliases into lower case
  -o, --overwrite       overwrite existing component
  -b, --database        store datasources in Configuration Server database
  -d DIRECTORY, --directory=DIRECTORY
                        output datasource directory
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -e EXTERNAL, --external=EXTERNAL
                        external configuration server
  -p XMLPACKAGE, --xml-package=XMLPACKAGE
                        xml template package
  -y ENTRYNAME, --entryname ENTRYNAME
                        entry group name (prefix)

Example
"""""""

.. code:: bash

	  nxscreate onlinecp
	  nxscreate onlinecp -c lambda
	  nxscreate onlinecp -c pilatus -b
	  nxscreate onlinecp -c lambda -d /home/user/xmldir/


nxscreate stdcomp
------------------

It creates a standard component from the xml template files
and its set of datasources.

Synopsis
""""""""

.. code:: bash

	  nxscreate stdcomp [options] [name1 value1 [name2 value2] ...]

- without '-t <type>': show a list of possible component types
- with '-t <type>  and without -c <component>: show a list of component variables for the given component type
- with -b: datasources are created in Configuration Server database
- without -b: datasources are created on the local filesystem in -d <directory>
- default <directory> is '.'
- [name1 value1 [name2 value2] ...] sequence  defines component variable values 

Options:
  -h, --help            show this help message and exit
  -c COMPONENT, --component=COMPONENT
                        component name
  -t CPTYPE, --type=CPTYPE
                        component type
  -r SERVER, --server=SERVER
                        configuration server device name
  -p XMLPACKAGE, --xml-package=XMLPACKAGE
                        xml template package
  -n, --nolower         do not change aliases into lower case
  -o, --overwrite       overwrite existing component
  -m, --mandatory       set the component as mandatory
  -b, --database        store datasources in Configuration Server database
  -d DIRECTORY, --directory=DIRECTORY
                        output datasource directory
  -e EXTERNAL, --external=EXTERNAL
                        external configuration server
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -y ENTRYNAME, --entryname ENTRYNAME
                        entry group name (prefix)

			
Example
"""""""

.. code:: bash

          nxscreate stdcomp  
          nxscreate stdcomp -t source
          nxscreate stdcomp -t slit -c -b front_slit1 xgap slt1x ygap slt1y
          nxscreate stdcomp -t default -c default -b -m


nxscreate comp
--------------

It creates a set of simple components.

Synopsis
""""""""

.. code:: bash

	  nxscreate comp [options] [name1] [name2] ...

- with -b: datasources are created in Configuration Server database
- without -b: datasources are created on the local filesystem in -d <directory>
- default <directory> is '.'
- default <server> is taken from Tango DB
- default <strategy> is step
- default <type> is NX_FLOAT
- default <chunk> is SCALAR
- default <nexuspath> is "/\$var.entryname#'scan'$var.serialno:NXentry/instrument/collection/"

Options:
  -h, --help            show this help message and exit
  -v DEVICE, --device-prefix=DEVICE
                        device prefix, i.e. exp_c
  -f FIRST, --first=FIRST
                        first index
  -l LAST, --last=LAST  last index
  -o, --overwrite       overwrite existing components
  -d DIRECTORY, --directory=DIRECTORY
                        output component directory
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -n NEXUSPATH, --nexuspath=NEXUSPATH
                        nexus path with field name
  -g STRATEGY, --strategy=STRATEGY
                        writing strategy, i.e. STEP, INIT, FINAL, POSTRUN
  -s DATASOURCE, --datasource-prefix DATASOURCE
                        datasource-prefix or datasourcename
  -t TYPE, --type=TYPE  nexus type of the field
  -u UNITS, --units=UNITS
                        nexus units of the field
  -k, --links           create datasource links
  -b, --database        store components in Configuration Server database
  -r SERVER, --server=SERVER
                        configuration server device name
  -c CHUNK, --chunk=CHUNK
                        chunk format, i.e. SCALAR, SPECTRUM, IMAGE
  -m, --minimal_device  device name without first '0'

Example
"""""""

.. code:: bash

	  nxscreate comp counter
	  nxscreate comp -f1 -l3 -v exp_c -b
	  nxscreate comp lambda -d /home/user/xmldir/
	  nxscreate comp -n "/\$var.entryname#'scan'\$var.serialno:NXentry/instrument/sis3302:NXdetector/collection:NXcollection/' -v sis3302_1_roi -f1 -l4  -g STEP -t NX_FLOAT64 -k -b -m
	  nxscreate comp -n "/\$var.entryname#'scan'\$var.serialno:NXentry/instrument/eh1_mca01:NXdetector/data" eh1_mca01 -g STEP -t NX_FLOAT64 -i -b -c SPECTRUM


nxscreate compare
-----------------

It compares two online.xml files

Synopsis
""""""""

.. code:: bash

	  nxscreate compare [-h] [-n] online_file [online_file]

- default: second <online_file> is '/online_dir/online.xml' if only file is given

positional arguments:
  online_file    online.xml files

optional arguments:
  -h, --help     show this help message and exit
  -n, --nolower  do not change aliases into lower case


Example
"""""""

.. code:: bash

	  nxscreate onlineds /online_dir/online.xml online.xml 
	  nxscreate compare online.xml
