Welcome to nxstools's documentation!
====================================

Authors: Jan Kotanski, Eugen Wintersberger, Halil Pasic
Introduction


-------------------------
Installation from sources
-------------------------

Install the dependencies:

    PyTango

Download the latest NXS Tools version from

    https://github.com/jkotan/nexdatas.tools/

Extract sources and run

$ python setup.py install


=======
nxsdata
=======

The nxsdata program is a command-line interface to Nexus Data Tango Server.
Program allows one to store NeXuS Data in H5 files.
The writer provides storing data from other Tango devices, various databases
as well as passed by a user client via JSON strings.


Usage: nxsdata <command> [-s <nexus_server>]  [<arg1> [<arg2>  ...]]
 e.g.: nxsdata openfile -s p02/tangodataserver/exp.01  $HOME/myfile.h5

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


=========
nxsconfig
=========

The nxsconfig program
is a command-line interface to NXS Configuration Tango Server.
It allows one to read XML configuration datasources
and components. It also gives possibility to
perform the process of component merging.


Usage: nxsconfig <command> [-s <config_server>]  [-d] [-m] [-n] [<name1>] [<name2>] [<name3>] ...
 e.g.: nxsconfig list -s p02/xmlconfigserver/exp.01 -d

Commands:
   list [-s <config_server>] [-m]
          list names of available components
   list -d [-s <config_server>]
          list names of available datasources
   show [-s <config_server>] [-m] component_name1 component_name2 ...
          show components with given names
   show -d [-s <config_server>] dsource_name1 dsource_name2 ...
          show datasources with given names
   get [-s <config_server>]  [-m] component_name1 component_name2 ...
          get merged configuration of components
   sources [-s <config_server>] [-m] component_name1 component_name2 ...
          get a list of component datasources
   components [-s <config_server>] component_name1 component_name2 ...
          get a list of dependent components
   variables [-s <config_server>] [-m] component_name1 component_name2 ...
          get a list of component variables
   data [-s <config_server>] json_data
          set values of component variables
   record [-s <config_server>]  component_name1
          get a list of datasource record names from component
   record -d [-s <config_server>] datasource_name1
          get a list of datasource record names
   servers [-s <config_server/host>]
          get lists of configuration servers from the current tango host
   describe [-s <config_server>] [-m | -p] component_name1 component_name2 ...
          show all parameters of given components
   describe|info -d [-s <config_server>] dsource_name1 dsource_name2 ...
          show all parameters of given datasources
   info [-s <config_server>] [-m | -p] component_name1 component_name2 ...
          show source parameters of given components
   geometry [-s <config_server>] [-m | -p] component_name1 component_name2 ...
          show transformation parameters of given components

Options:
  -h, --help            show this help message and exit
  -s SERVER, --server=SERVER
                        configuration server device name
  -d, --datasources     perform operation on datasources
  -m, --mandatory       make use mandatory components as well
  -p, --private         make use private components, i.e. starting with '__'
  -n, --no-newlines     split result with space characters

=========
nxscreate
=========

The nxscreate program allows one to create simple datasources and components.

Usage: nxscreate  <command> [ <options>]  [<arg1> [<arg2>  ...]]


The following commands are available:


nxscreate clientds [options] [name1] [name2]
--------------------------------------------

It creates a set of client datasources.

Options:
  -h, --help            show this help message and exit
  -p DEVICE, --device-prefix=DEVICE
                        device prefix, i.e. exp_c
  -f FIRST, --first=FIRST
                        first index
  -l LAST, --last=LAST  last index
  -d DIRECTORY, --directory=DIRECTORY
                        output datasource directory
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -b, --database        store components in Configuration Server database
  -m, --minimal_device  device name without first '0'
  -r SERVER, --server=SERVER
                        configuration server device name

e.g.:
	nxscreate_clientds -f 1 -l2 -p haso.desy.de:10000/expchan/sis3820_exp/ -s exp_c -m -b -r test/nxsconfigserver/01

nxscreate tangods [options]
---------------------------

It creates a set of TANGO datasources.

Options:
  -h, --help            show this help message and exit
  -p DEVICE, --device-prefix=DEVICE
                        device prefix, i.e. exp_c
  -f FIRST, --first=FIRST
                        first index
  -l LAST, --last=LAST  last index
  -a ATTRIBUTE, --attribute=ATTRIBUTE
                        tango attribute name
  -o DATASOURCE, --datasource-prefix=DATASOURCE
                        datasource-prefix
  -d DIRECTORY, --directory=DIRECTORY
                        output datasource directory
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -s HOST, --host=HOST  tango host name
  -t PORT, --port=PORT  tango host port
  -b, --database        store components in Configuration Server database
  -r SERVER, --server=SERVER
                        configuration server device name


nxscreate deviceds [options] [dv_attr1 [dv_attr2 [dv_attr3 ...]]]
-----------------------------------------------------------------

It creates a set of TANGO datasources for all device attributes.

Options:
  -h, --help            show this help message and exit
  -v DEVICE, --device=DEVICE
                        device, i.e. p09/pilatus300k/01
  -o DATASOURCE, --datasource-prefix=DATASOURCE
                        datasource-prefix
  -d DIRECTORY, --directory=DIRECTORY
                        output datasource directory
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -s HOST, --host=HOST  tango host name
  -t PORT, --port=PORT  tango host port
  -b, --database        store components in Configuration Server database
  -n, --no-group        creates common group with a name of datasource prefix
  -r SERVER, --server=SERVER
                        configuration server device name

nxscreate onlineds [options] inputFile
--------------------------------------

It creates a set of motor datasources from an online xml file.

Usage: ndtscreate_onlineds [options] inputFile
       nxscreate onlineds [options] inputFile
e.g.
       nxscreate onlineds -b
       nxscreate onlinecp -d /home/user/xmldir

 - with -b datasources are created in Configuration Server database
 - with -d <directory> datasources are created on filesystem
 - default <inputFile> is '/online_dir/online.xml'


Options:
  -h, --help            show this help message and exit
  -b, --database        store components in Configuration Server database
  -d DIRECTORY, --directory=DIRECTORY
                        output directory where datasources will be saved
  -n, --nolower         do not change aliases into lower case
  -r SERVER, --server=SERVER
                        configuration server device name
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter


nxscreate onlinecp [options] inputFile
--------------------------------------
Usage: ndtscreate_onlinecp [options] [<inputFile>]
       nxscreate onlinecp [options] [<inputFile>]
e.g.
       nxscreate onlinecp
       nxscreate onlinecp -c pilatus

 - without '-c <component>' a list of possible components is shown
 - without '-d <dircetory>  datasources are created in Configuration Server database
 - with -d <directory> datasources are created on filesystem
 - default <inputFile> is '/online_dir/online.xml'


Options:
  -h, --help            show this help message and exit
  -c COMPONENT, --component=COMPONENT
                        component namerelated to the device name from
                        <inputFile>
  -r SERVER, --server=SERVER
                        configuration server device name
  -n, --nolower         do not change aliases into lower case
  -o, --overwrite       overwrite existing component
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -d DIRECTORY, --directory=DIRECTORY
                        output directory where datasources will be stored.
			If it is not set components are stored in Configuration
                        Server database



nxscreate comp [options] [name1] [name2] ...
--------------------------------------------

It creates a set of simple components.

Options:
  -h, --help            show this help message and exit
  -p DEVICE, --device-prefix=DEVICE
                        device prefix, i.e. exp_c
  -f FIRST, --first=FIRST
                        first index
  -l LAST, --last=LAST  last index
  -d DIRECTORY, --directory=DIRECTORY
                        output component directory
  -x FILE, --file-prefix=FILE
                        file prefix, i.e. counter
  -n NEXUSPATH, --nexuspath=NEXUSPATH
                        nexus path with field name
  -s STRATEGY, --strategy=STRATEGY
                        writing strategy, i.e. STEP, INIT, FINAL, POSTRUN
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