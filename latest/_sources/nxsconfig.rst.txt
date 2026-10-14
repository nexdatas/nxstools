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

	  nxsconfig <command> [-s <config_server>]  [-d] [-r] [-m] [-n] [-p] [<name1>] [<name2>] [<name3>] ...

Commands:
   list [-s <config_server>] [-m] [-p] [-n]
          list names of available components
   list -d [-s <config_server>] [-n]
          list names of available datasources
   list -r [-s <config_server>] [-n]
          list names of available profiles
   show [-s <config_server>] [-m] [-o <dir>] component_name1 component_name2 ...
          show components with given names
   show -d [-s <config_server>]  [-o <dir>] dsource_name1 dsource_name2 ...
          show datasources with given names
   show -r [-s <config_server>]  [-o <dir>] profile_name1 profile_name2 ...
          show profiles with given names
   upload [-s <config_server>] [-m] [-i <dir>] [-f] component_name1 component_name2 ...
          load components from given files
   upload -d [-s <config_server>]  [-i <dir>] [-f] dsource_name1 dsource_name2 ...
          load datasources from given files
   upload -r [-s <config_server>]  [-i <dir>] [-f] profile_name1 profile_name2 ...
          load profiles from given files
   get [-s <config_server>]  [-n] component_name1 component_name2 ...
          get merged configuration of components
   delete [-s <config_server>] [-f] component_name1 component_name2 ...
          delete components with given names
   delete -d [-s <config_server>] [-f] dsource_name1 dsource_name2 ...
          delete datasources with given names
   delete -r [-s <config_server>] [-f] profile_name1 profile_name2 ...
          delete profiles with given names
   sources [-s <config_server>] [-m] [-n] component_name1 component_name2 ...
          get a list of component datasources
   components [-s <config_server>] [-n] component_name1 component_name2 ...
          get a list of dependent components
   variables [-s <config_server>] [-m] [-n] component_name1 component_name2 ...
          get a list of component variables
   data [-s <config_server>] json_data
          set values of component variables
   record [-s <config_server>] [-n] component_name1
          get a list of datasource record names from component
   record -d [-s <config_server>] [-n] datasource_name1
          get a list of datasource record names
   servers [-s <config_server/host>] [-n]
          get lists of configuration servers from the current tango host
   describe [-s <config_server>] [-m | -p] [-n] component_name1 component_name2 ...
          show all parameters of given components
   describe|info -d [-s <config_server>] [-n] dsource_name1 dsource_name2 ...
          show all parameters of given datasources
   info [-s <config_server>] [-m | -p] [-n] component_name1 component_name2 ...
          show source parameters of given components
   info -r [-s <config_server>]  [-n] profile_name1 profile_name2 ...
          show general parameters of given profiles
   geometry [-s <config_server>] [-m | -p] [-n] component_name1 component_name2 ...
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
