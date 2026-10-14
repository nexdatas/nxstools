=========
nxsconfig
=========

Description
-----------

The nxsconfig program
is a command-line interface to NXS Configuration Tango Server.
It allows one to read XML configuration datasources
and components. It also gives possibility to
perform the process of component merging.

Synopsis
--------

.. code:: bash

	  nxsconfig <command> [-s <config_server>]  [-d] [-m] [-n] [<name1>] [<name2>] [<name3>] ...

Commands:
   list [-s <config_server>] [-m]
          list names of available components
   list -d [-s <config_server>]
          list names of available datasources
   show [-s <config_server>] component_name1 component_name2 ...
          show components with given names
   show -d [-s <config_server>] dsource_name1 dsource_name2 ...
          show datasources with given names
   get [-s <config_server>]  [-m] component_name1 component_name2 ...
          get merged configuration of components
   delete [-s <config_server>] [-f] component_name1 component_name2 ...
          delete components with given names
   delete -d [-s <config_server>] [-f] dsource_name1 dsource_name2 ...
          delete datasources with given names
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
  -f, --force           do not ask

Example
-------

.. code:: bash

	  nxsconfig list -s p02/xmlconfigserver/exp.01 -d
	  nxsconfig info
	  nxsconfig geometry
