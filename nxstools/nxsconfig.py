#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2018 DESY, Jan Kotanski <jkotan@mail.desy.de>
#
#    nexdatas is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    nexdatas is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with nexdatas.  If not, see <http://www.gnu.org/licenses/>.
#

""" Command-line tool for ascess to the nexdatas configuration server """

import sys
import os
import argparse
import json
from .nxsparser import ParserTools, TableTools, TableDictTools, ESRFConverter
from .nxsargparser import (Runner, NXSArgParser, ErrorException)
from .nxsdevicetools import (checkServer, listServers, openServer)
#: (:obj:`bool`) True if tango available

PYTANGO = False
try:
    try:
        import tango
    except Exception:
        import PyTango as tango
    PYTANGO = True
except Exception:
    pass

if sys.version_info > (3,):
    raw_input = input


class ConfigServer(object):

    """ configuration server adapter
    """

    def __init__(self, device, nonewline=False):
        """ constructor

        :param device: device name of the configuration server
        :type device: :obj:`str`
        :param nonewline: if the output should not be separated
                          by the new line character
        :type nonewline: :obj:`bool`
        """
        #: (:obj:`str`) spliting character
        self.char = " " if nonewline else "\n"
        #: (:class:`tango.DeviceProxy`) configuration server proxy
        self._cnfServer = openServer(device)
        self._cnfServer.Open()

    def listCmd(self, ds, mandatory=False, private=False, profiles=False):
        """ lists the DB item names

        :param ds: flag set True for datasources
        :type ds: :obj:`bool`
        :param mandatory: flag set True for mandatory components
        :type mandatory: :obj:`bool`
        :param private: flag set True for components starting with '__'
        :type private: :obj:`bool`
        :param profiles: flag set True for profiles
        :type profiles: :obj:`bool`
        :returns: list op item names
        :rtype: :obj:`list` <:obj:`str`>
        """

        if ds:
            if not mandatory:
                return self._cnfServer.AvailableDataSources()
        elif profiles:
            return self._cnfServer.AvailableSelections()
        else:
            if mandatory:
                return self._cnfServer.MandatoryComponents()
            elif private:
                return [cp for cp in self._cnfServer.AvailableComponents()
                        if cp.startswith("__")]
            else:
                return [cp for cp in self._cnfServer.AvailableComponents()
                        if not cp.startswith("__")]
        return []

    def sourcesCmd(self, components, mandatory=False):
        """ lists datasources of the components

        :param components: given components
        :type components: :obj:`list` <:obj:`str`>
        :returns: list of datasource names
        :rtype: :obj:`list` <:obj:`str`>
        """
        cmps = self._cnfServer.AvailableComponents()
        result = []
        for component in components:
            if component not in cmps:
                sys.stderr.write("Error: Component '%s' not stored in "
                                 "the configuration server\n" % component)
                sys.stderr.flush()
                return []
        if not mandatory:
            for component in components:
                result.extend(self._cnfServer.ComponentDataSources(component))
        else:
            result = self._cnfServer.ComponentsDataSources(components)

        return result

    def componentsCmd(self, components):
        """ lists components of the components

        :param components: given components
        :type components: :obj:`list` <:obj:`str`>
        :returns: list of component names
        :rtype: :obj:`list` <:obj:`str`>
        """
        cmps = self._cnfServer.AvailableComponents()
        result = []
        for component in components:
            if component not in cmps:
                sys.stderr.write("Error: Component '%s' not stored in "
                                 "the configuration server\n" % component)
                sys.stderr.flush()
                return []
        result = self._cnfServer.DependentComponents(components)

        return result

    def variablesCmd(self, components, mandatory=False):
        """ lists variable of the components

        :param components: given components
        :type components: :obj:`list` <:obj:`str`>
        :returns: list of datasource names
        :rtype: :obj:`list` <:obj:`str`>
        """
        cmps = self._cnfServer.AvailableComponents()
        result = []
        for component in components:
            if component not in cmps:
                sys.stderr.write("Error: Component '%s' not stored in "
                                 "the configuration server\n" % component)
                sys.stderr.flush()
                return []
        if not mandatory:
            for component in components:
                result.extend(self._cnfServer.ComponentVariables(component))
        else:
            result = self._cnfServer.ComponentsVariables(components)

        return result

    def __getDataSources(self, name):
        """ provides datasources and its records for a given component

        :param name: given component or datasource
        :type name: :obj:`str`
        :returns: tuple with names and records
        :rtype: (:obj:`str` , :obj:`str`)
        """
        records = []
        names = []
        interNames = []
        xmlcp = self._cnfServer.Components([name])
        for xmlc in xmlcp:
            dslist = ParserTools.parseDataSources(xmlc)
            for ds in dslist:
                if ds["source_name"]:
                    interNames.append(ds["source_name"])
                if ds["source"]:
                    records.append(ds["source"])

            allNames = self._cnfServer.ComponentDataSources(name)
            for nm in allNames:
                if nm not in interNames:
                    names.append(nm)
        return (names, records)

    def recordCmd(self, ds, name):
        """ lists datasources of the component

        :param ds: flag set True for datasources
        :type ds: :obj:`bool`
        :param name: given component or datasource
        :type name: :obj:`str`
        :returns: list of record names
        :rtype: :obj:`list` <:obj:`str`>
        """
        if not name:
            return []
        name = name[0]
        if not ds:
            cmps = self._cnfServer.AvailableComponents()
            if name not in cmps:
                sys.stderr.write("Error: Component '%s' not stored in "
                                 "the configuration server\n" % name)
                sys.stderr.flush()
                return []
            names, records = self.__getDataSources(name)
        else:
            names = [name]
            records = []

        dsrcs = self._cnfServer.AvailableDataSources()
        for nm in names:
            if nm not in dsrcs:
                sys.stderr.write("Error: Datasource '%s' not stored in "
                                 "the configuration server\n" % nm)
                sys.stderr.flush()
                return []

        xmls = self._cnfServer.DataSources(names)
        for xml in xmls:
            if xml:
                try:
                    rec = ParserTools.parseRecord(xml)
                    if rec:
                        records.append(rec)
                except Exception:
                    sys.stderr.write(
                        "Error: Datasource '%s' cannot be parsed\n" % xml)
                    sys.stderr.write(str(sys.exc_info()[0]) + ": "
                                     + str(sys.exc_info()[1]) + '\n')
                    sys.stderr.flush()
                    return []
        return records

    def showCmd(self, ds, args, mandatory=False, profiles=False,
                directory=None):
        """ shows the DB items

        :param ds: flag set True for datasources
        :type ds: :obj:`bool`
        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param mandatory: flag set True for mandatory components
        :type mandatory: :obj:`bool`
        :param profiles: flag set True for profiles
        :type profiles: :obj:`bool`
        :param directory: output file directory
        :type directory: :obj:`str`
        :returns: list of XML items
        :rtype: :obj:`list` <:obj:`str`>
        """
        if ds:
            dsrc = self._cnfServer.AvailableDataSources()
            for ar in args:
                if ar not in dsrc:
                    sys.stderr.write("Error: DataSource '%s' not stored in "
                                     "the configuration server\n" % ar)
                    sys.stderr.flush()
                    return []
            elems = self._cnfServer.DataSources(args)
            if not directory:
                return elems
            else:
                for i, ar in enumerate(args):
                    name = os.path.join(
                        directory, "%s.ds.xml" % ar.replace("/", "_"))
                    with open(name, "w") as text_file:
                        text_file.write(elems[i])

        elif profiles:
            dsrc = self._cnfServer.AvailableSelections()
            for ar in args:
                if ar not in dsrc:
                    sys.stderr.write("Error: Profile '%s' not stored in "
                                     "the configuration server\n" % ar)
                    sys.stderr.flush()
                    return []
            elems = self._cnfServer.Selections(args)
            if not directory:
                return elems
            else:
                for i, ar in enumerate(args):
                    name = os.path.join(
                        directory, "%s.json" % ar.replace("/", "_"))
                    with open(name, "w") as text_file:
                        text_file.write(elems[i])
        else:
            cmps = self._cnfServer.AvailableComponents()
            for ar in args:
                if ar not in cmps:
                    sys.stderr.write("Error: Component '%s' not stored in "
                                     "the configuration server\n" % ar)
                    sys.stderr.flush()
                    return []
            if mandatory:
                mand = list(self._cnfServer.MandatoryComponents())
                mand.extend(args)
                elems = self._cnfServer.Components(mand)
            else:
                elems = self._cnfServer.Components(args)
                mand = args
            if not directory:
                return elems
            else:
                for i, ar in enumerate(mand):
                    name = os.path.join(
                        directory, "%s.xml" % ar.replace("/", "_"))
                    with open(name, "w") as text_file:
                        text_file.write(elems[i])
        return []

    def deleteCmd(self, ds, args, ask=True, profiles=False):
        """ delete the DB items

        :param ds: flag set True for datasources
        :type ds: :obj:`bool`
        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param ask: ask flag
        :type ask: :obj:`bool`
        :param profiles: flag set True for profiles
        :type profiles: :obj:`bool`
        :returns: list of XML items
        :rtype: :obj:`list` <:obj:`str`>
        """
        valid = {"yes": True, "y": True, "ye": True,
                 "no": False, "n": False}
        default = "y"
        label = "Component"
        if ds:
            dsrc = self._cnfServer.AvailableDataSources()
            label = "DataSource"
        elif profiles:
            dsrc = self._cnfServer.AvailableSelections()
            label = "Profile"
        else:
            dsrc = self._cnfServer.AvailableComponents()
        for ar in args:
            if ar not in dsrc:
                sys.stderr.write(
                    "Error: %s '%s' not stored in "
                    "the configuration server\n" % (label, ar))
                sys.stderr.flush()
                return []
        for ar in args:
            choice = default
            if ask:
                choice = raw_input("Remove %s '%s'? [Y/n] \n" % (
                    label, ar)).lower()
                while True:
                    if choice == '':
                        choice = default
                        break
                    elif choice in valid:
                        break
                    else:
                        sys.stdout.write("Please respond with 'yes' or 'no' "
                                         "(or 'y' or 'n').\n")
                        sys.stdout.flush()
            if valid[choice]:
                if ds:
                    self._cnfServer.DeleteDataSource(ar)
                elif profiles:
                    self._cnfServer.DeleteSelection(ar)
                else:
                    self._cnfServer.DeleteComponent(ar)
        return []

    def uploadCmd(self, ds, args, force=False, profiles=False, directory='.',
                  mandatory=False, external=None):
        """ upload the DB items from files

        :param ds: flag set True for datasources
        :type ds: :obj:`bool`
        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param force: force flag
        :type force: :obj:`bool`
        :param profiles: flag set True for profiles
        :type profiles: :obj:`bool`
        :param directory: input file directory
        :type directory: :obj:`str`
        :param mandatory: mandatory flag
        :type mandatory: :obj:`bool`
        :param external: external import type
        :type external: :obj:`str`
        :returns: list of XML items
        :rtype: :obj:`list` <:obj:`str`>
        """
        label = "Component"
        if ds:
            dsrc = self._cnfServer.AvailableDataSources()
            label = "DataSource"
        elif profiles:
            dsrc = self._cnfServer.AvailableSelections()
            label = "Profile"
        else:
            dsrc = self._cnfServer.AvailableComponents()
        if not force:
            for ar in args:
                if ar in dsrc:
                    sys.stderr.write(
                        "Error: %s '%s' is stored in "
                        "the configuration server\n" % (label, ar))
                    sys.stderr.flush()
                    return []
        for ar in args:
            if ds:
                name = os.path.join(
                    directory, "%s.ds.xml" % ar.replace("/", "_"))
                with open(name, 'r') as fl:
                    txt = fl.read()
                self._cnfServer.XMLString = txt
                self._cnfServer.StoreDataSource(ar)
            elif profiles:
                name = os.path.join(
                    directory, "%s.json" % ar.replace("/", "_"))
                with open(name, 'r') as fl:
                    txt = fl.read()
                self._cnfServer.Selection = txt
                self._cnfServer.StoreSelection(ar)
            else:
                name = os.path.join(
                    directory, "%s.xml" % ar.replace("/", "_"))
                with open(name, 'r') as fl:
                    txt = fl.read()
                if external and external.lower() == "esrf":
                    txt = ESRFConverter().convert(txt)
                self._cnfServer.XMLString = txt
                self._cnfServer.StoreComponent(ar)
                if mandatory:
                    self._cnfServer.SetMandatoryComponents([ar])

        return []

    def getCmd(self, args):
        """ provides final configuration

        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :returns: XML configuration string
        :rtype: :obj:`str`
        """
        cmps = self._cnfServer.AvailableComponents()
        for ar in args:
            if ar not in cmps:
                sys.stderr.write(
                    "Error: Component '%s' not stored in "
                    "the configuration server\n" % ar)
                sys.stderr.flush()
                return ""
        self._cnfServer.CreateConfiguration(args)
        return self._cnfServer.XMLString

    def __describeDataSources(self, args, headers=None, filters=None):
        """ provides description of datasources

        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param headers: list of output parameters
        :type headers: :obj:`list` <:obj:`str`>
        :param filters:  filters for first column names
        :type filters: :obj:`list` <:obj:`str`>
        :returns: list with description
        :rtype: :obj:`list` <:obj:`str`>
        """
        xmls = ""
        parameters = []
        description = []
        dss = self._cnfServer.AvailableDataSources()
        if not dss:
            sys.stderr.write(
                "\n'%s' does not have any datasources\n\n"
                % self._cnfServer.name())
            sys.stderr.flush()
            return ""
        for ar in args:
            if ar not in dss:
                sys.stderr.write(
                    "Error: DataSource '%s' not stored in "
                    "the configuration server\n" % ar)
                sys.stderr.flush()
                return ""
        headers = headers or ["source_type", "source"]
        if args:
            dsxmls = self._cnfServer.DataSources(args)
            for i, xmls in enumerate(dsxmls):
                parameters = ParserTools.parseDataSources(xmls)
                ttools = TableTools(parameters,
                                    headers=headers,
                                    filters=filters)
                ttools.title = "DataSource: '%s'" % args[i]
                description.extend(ttools.generateList())
        else:
            dsxmls = self._cnfServer.DataSources(dss)
            xmls = ParserTools.mergeDefinitions(dsxmls).strip()
            parameters.extend(ParserTools.parseDataSources(xmls))
            if "source_name" not in headers:
                headers = ["source_name"].extend(headers)
            ttools = TableTools(parameters,
                                headers=headers,
                                filters=filters)
            description.extend(ttools.generateList())

        if not description:
            sys.stderr.write(
                "\nHint: add datasource names as command arguments "
                "or -m for mandatory components \n\n")
            sys.stderr.flush()
            return ""
        return description

    def __describeProfiles(self, args, headers=None):
        """ provides description of datasources

        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param headers: list of output parameters
        :type headers: :obj:`list` <:obj:`str`>
        :returns: list with description
        :rtype: :obj:`list` <:obj:`str`>
        """
        xmls = ""
        parameters = []
        description = []
        dss = self._cnfServer.AvailableSelections()
        if not dss:
            sys.stderr.write(
                "\n'%s' does not have any profiles\n\n"
                % self._cnfServer.name())
            sys.stderr.flush()
            return ""
        for ar in args:
            if ar not in dss:
                sys.stderr.write(
                    "Error: Profile '%s' not stored in "
                    "the configuration server\n" % ar)
                sys.stderr.flush()
                return ""
        args = args or dss
        dsxmls = self._cnfServer.Selections(args)
        for i, xmls in enumerate(dsxmls):
            parameters = [json.loads(xmls)]
            ttools = TableDictTools(parameters)
            ttools.title = "Profile: '%s'" % args[i]
            if headers:
                ttools.headers = headers
            description.extend(ttools.generateList())

        if not description:
            sys.stderr.write(
                "\nHint: add profile names as command arguments "
                "or -m for mandatory components \n\n")
            sys.stderr.flush()
            return ""
        return description

    def __describeComponents(self, args, headers=None, nonone=None,
                             private=False, attrs=True, filters=None):
        """ provides description of components

        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param headers: list of output parameters
        :type headers: :obj:`list` <:obj:`str`>
        :param nonone: list of parameters which have to exist to be shown
        :type nonone: :obj:`list` <:obj:`str`>
        :param private: flag set True for components starting with '__'
        :type private: :obj:`bool`
        :param attrs: flag set True for parsing attributes
        :type attrs: :obj:`bool`
        :param filters:  filters for first column names
        :type filters: :obj:`list` <:obj:`str`>
        :returns: list with description
        :rtype: :obj:`list` <:obj:`str`>
        """
        xmls = ""
        parameters = []
        description = []
        cmps = self._cnfServer.AvailableComponents()
        if not cmps:
            sys.stderr.write(
                "\n'%s' does not have any components\n\n"
                % self._cnfServer.name())
            sys.stderr.flush()
            return ""
        dargs = []
        deps = {}
        for ar in args:
            dargs.append(ar)
            if ar not in cmps:
                sys.stderr.write(
                    "Error: Component '%s' not stored in "
                    "the configuration server\n" % ar)
                sys.stderr.flush()
                return ""
            else:
                dars = self._cnfServer.dependentComponents([ar])
                dars = list(set(dars) - set([ar]))
                if dars:
                    dargs.extend(dars)
                    deps[ar] = dars

        if not dargs:
            if private:
                dargs = [cp for cp in cmps if cp.startswith("__")]
            else:
                dargs = [cp for cp in cmps if not cp.startswith("__")]
        dargs = dargs or cmps
        if dargs:
            try:
                cpxmls = self._cnfServer.instantiatedComponents(dargs)
            except Exception:
                cpxmls = []
                for ar in dargs:
                    try:
                        cpxmls.extend(
                            self._cnfServer.instantiatedComponents([ar]))
                    except Exception:
                        cpxmls.extend(self._cnfServer.Components([ar]))
                        sys.stderr.write(
                            "Error: Component '%s' cannot be instantiated\n"
                            % ar)
                        sys.stderr.flush()

            for i, xmls in enumerate(cpxmls):
                parameters = ParserTools.parseFields(xmls)
                if attrs:
                    parameters.extend(ParserTools.parseAttributes(xmls))
                parameters.extend(ParserTools.parseLinks(xmls))
                ttools = TableTools(parameters, nonone,
                                    headers,
                                    filters)
                if dargs[i] in deps:
                    ttools.title = "Component: '%s' %s" % (
                        dargs[i], deps[dargs[i]])
                else:
                    ttools.title = "Component: '%s'" % dargs[i]
                description.extend(ttools.generateList())
        if not description:
            sys.stderr.write(
                "\nHint: add component names as command arguments "
                "or -m for mandatory components \n\n")
            sys.stderr.flush()
            return ""
        return description

    def __describeConfiguration(self, args, headers=None, nonone=None,
                                attrs=True, filters=None):
        """ provides description of final configuration

        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param headers: list of output parameters
        :type headers: :obj:`list` <:obj:`str`>
        :param nonone: list of parameters which have to exist to be shown
        :type nonone: :obj:`list` <:obj:`str`>
        :param attrs: flag set True for parsing attributes
        :type attrs: :obj:`bool`
        :param filters:  filters for first column names
        :type filters: :obj:`list` <:obj:`str`>
        :returns: list with description
        :rtype: :obj:`list` <:obj:`str`>
        """
        xmls = ""
        description = []
        cmps = self._cnfServer.AvailableComponents()
        if not cmps:
            sys.stderr.write(
                "\n'%s' does not have any components\n\n"
                % self._cnfServer.name())
            sys.stderr.flush()
            return ""
        for ar in args:
            if ar not in cmps:
                sys.stderr.write(
                    "Error: Component '%s' not stored in "
                    "the configuration server\n" % ar)
                sys.stderr.flush()
                return ""

        self._cnfServer.CreateConfiguration(args)
        xmls = str(self._cnfServer.XMLString).strip()
        if xmls:
            description.extend(ParserTools.parseFields(xmls))
            if attrs:
                description.extend(ParserTools.parseAttributes(xmls))
            description.extend(ParserTools.parseLinks(xmls))
        if not description:
            sys.stderr.write(
                "\nHint: add components as command arguments "
                "or -m for mandatory components \n\n")
            sys.stderr.flush()
            return ""
        ttools = TableTools(description, nonone,
                            headers=headers,
                            filters=filters)
        if headers:
            ttools.headers = headers
        return ttools.generateList()

    def describeCmd(self, ds, args, md, pr, headers=None, filters=None):
        """ provides description of configuration elements

        :param ds: flag set True for datasources
        :type ds: :obj:`bool`
        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param md: flag set True for mandatory components
        :type md: :obj:`bool`
        :param pr: flag set True for private components
        :type pr: :obj:`bool`
        :param pr: column headers
        :type pr: :obj:`str`
        :param filters:  filters for first column names separated by comma
        :type filters: :obj:`str`
        :returns: list with description
        :rtype: :obj:`list` <:obj:`str`>

        """
        if headers:
            headers = str(headers).split(',')
        else:
            headers = None
        if filters:
            filters = str(filters).split(',')
        else:
            filters = None
        if ds:
            return self.__describeDataSources(args, headers, filters=filters)
        elif not md:
            return self.__describeComponents(
                args, headers, private=pr, filters=filters)
        else:
            return self.__describeConfiguration(
                args, headers, filters=filters)

    def infoCmd(self, ds, args, md, pr, profiles):
        """ Provides info for given elements

        :param ds: flag set True for datasources
        :type ds: :obj:`bool`
        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param md: flag set True for mandatory components
        :type md: :obj:`bool`
        :param pr: flag set True for private components
        :type pr: :obj:`bool`
        :param profiles: flag set True for profiles
        :type profiles: :obj:`bool`
        :returns: list with description
        :rtype: :obj:`list` <:obj:`str`>
        """

        cpheaders = [
            "source_name",
            "source_type",
            "nexus_type",
            "shape",
            "strategy",
            "source",
        ]
        nonone = ["source_name"]
        if ds:
            return self.__describeDataSources(args)
        elif profiles:
            return self.__describeProfiles(args)
        elif not md:
            return self.__describeComponents(args, cpheaders, nonone, pr)
        else:
            return self.__describeConfiguration(args, cpheaders, nonone)

    def geometryCmd(self, args, md, pr):
        """ provides geometry info for given elements

        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :param md: flag set True for mandatory components
        :type md: :obj:`bool`
        :param pr: flag set True for private components
        :type pr: :obj:`bool`
        :returns: list with description
        :rtype: :obj:`list` <:obj:`str`>
        """
        cpheaders = [
            "nexus_path",
            "source_name",
            "units",
            "trans_type",
            "trans_vector",
            "trans_offset",
            "depends_on",
        ]
        if not md:
            return self.__describeComponents(args, cpheaders, private=pr,
                                             attrs=False)
        else:
            return self.__describeConfiguration(args, cpheaders,
                                                attrs=False)

    def dataCmd(self, args):
        """ provides varaible values

        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :returns: JSON with variables
        :rtype: :obj:`str`
        """
        if args and len(args) > 0 and args[0]:
            self._cnfServer.Variables = args[0]
        return [str(self._cnfServer.Variables)]

    def mergeCmd(self, args):
        """ provides merged components

        :param args: list of item names
        :type args: :obj:`list` <:obj:`str`>
        :returns: XML configuration string with merged components
        :rtype: :obj:`str`
        """
        cmps = self._cnfServer.AvailableComponents()
        for ar in args:
            if ar not in cmps:
                sys.stderr.write(
                    "Error: Component '%s' not stored "
                    "in the configuration server\n" % ar)
                sys.stderr.flush()
                return ""
        return self._cnfServer.Merge(args)


class List(Runner):

    """ List runner"""

    #: (:obj:`str`) command description
    description = "list names of available components, datasources or profiles"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig list\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-d", "--datasources", action="store_true",
                            default=False, dest="datasources",
                            help="perform operation for datasources")
        parser.add_argument("-r", "--profiles", action="store_true",
                            default=False, dest="profiles",
                            help="perform operation for profiles")
        parser.add_argument("-m", "--mandatory", action="store_true",
                            default=False, dest="mandatory",
                            help="make use mandatory components")
        parser.add_argument("-p", "--private", action="store_true",
                            default=False, dest="private",
                            help="make use private components,"
                            " i.e. starting with '__'")
        parser.add_argument("-n", "--no-newlines", action="store_true",
                            default=False, dest="nonewlines",
                            help="split result with space characters")

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server, options.nonewlines)
        string = cnfserver.char.join(cnfserver.listCmd(
            options.datasources, options.mandatory, options.private,
            options.profiles
        ))
        return string


class Show(Runner):

    """ Show runner"""

    #: (:obj:`str`) command description
    description = "show (or write to files) " \
                  "components, datasources or profiles with given names"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig show dcm\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-d", "--datasources", action="store_true",
                            default=False, dest="datasources",
                            help="perform operation for datasources")
        parser.add_argument("-r", "--profiles", action="store_true",
                            default=False, dest="profiles",
                            help="perform operation for profiles")
        parser.add_argument("-o", "--directory", dest="directory",
                            help=("output file directory"))
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components, datasources '
                            'or profiles')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server, False)
        string = cnfserver.char.join(cnfserver.showCmd(
            options.datasources, options.args, False,
            options.profiles, options.directory
        ))
        return string


class Delete(Runner):

    """ Show runner"""

    #: (:obj:`str`) command description
    description = "delete components, datasources or profiles " \
                  "with given names from ConfigServer"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig delete pilatus1a\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-d", "--datasources", action="store_true",
                            default=False, dest="datasources",
                            help="perform operation for datasources")
        parser.add_argument("-r", "--profiles", action="store_true",
                            default=False, dest="profiles",
                            help="perform operation for profiles")
        parser.add_argument("-f", "--force", action="store_true",
                            default=False, dest="force",
                            help="do not ask")
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components, datasources '
                            'or profiles')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server, False)
        string = cnfserver.char.join(cnfserver.deleteCmd(
            options.datasources, options.args, not options.force,
            options.profiles
        ))
        return string


class Upload(Runner):

    """ Store runner"""

    #: (:obj:`str`) command description
    description = "upload components, datasources or profiles " \
        "with given names from locale filesystem into ConfigServer"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig upload exp_c01 exp_c02\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-d", "--datasources", action="store_true",
                            default=False, dest="datasources",
                            help="perform operation for datasources")
        parser.add_argument("-m", "--mandatory", action="store_true",
                            default=False, dest="mandatory",
                            help="set the component as mandatory")
        parser.add_argument("-r", "--profiles", action="store_true",
                            default=False, dest="profiles",
                            help="perform operation for profiles")
        parser.add_argument("-f", "--force", action="store_true",
                            default=False, dest="force",
                            help="do not ask")
        parser.add_argument("-i", "--directory", dest="directory",
                            default=".",
                            help=("input file directory, default: '.'"))
        parser.add_argument("-e", "--external", dest="external",
                            default="",
                            help=("external format of xml, e.g. 'esrf'"))
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components, datasources '
                            'or profiles')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server, False)
        string = cnfserver.char.join(cnfserver.uploadCmd(
            options.datasources, options.args, options.force,
            options.profiles, options.directory, options.mandatory,
            options.external
        ))
        return string


class Get(Runner):

    """ Get runner"""

    #: (:obj:`str`) command description
    description = "get full configuration of components"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig get  dcm source slit1 slit2\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server)
        string = str(cnfserver.getCmd(options.args))
        return string


class Merge(Runner):

    """ Merge runner"""

    #: (:obj:`str`) command description
    description = "get merged configuration of components or datasources"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig merge  slit1 dcm \n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server)
        string = str(cnfserver.getCmd(options.args))
        return string


class Sources(Runner):

    """ Sources runner"""

    #: (:obj:`str`) command description
    description = "get a list of component datasources"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig sources slit1\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-m", "--mandatory", action="store_true",
                            default=False, dest="mandatory",
                            help="make use mandatory components")
        parser.add_argument("-n", "--no-newlines", action="store_true",
                            default=False, dest="nonewlines",
                            help="split result with space characters")
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server, options.nonewlines)
        string = cnfserver.char.join(cnfserver.sourcesCmd(
            options.args, options.mandatory))
        return string


class Components(Runner):

    """ Components runner"""

    #: (:obj:`str`) command description
    description = "get a list of dependent components"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig components dcm\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-n", "--no-newlines", action="store_true",
                            default=False, dest="nonewlines",
                            help="split result with space characters")
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server, options.nonewlines)
        string = cnfserver.char.join(cnfserver.componentsCmd(
            options.args))
        return string


class Variables(Runner):

    """ Variables runner"""

    #: (:obj:`str`) command description
    description = "get a list of component variables"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig variables dcm\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-m", "--mandatory", action="store_true",
                            default=False, dest="mandatory",
                            help="make use mandatory components")
        parser.add_argument("-n", "--no-newlines", action="store_true",
                            default=False, dest="nonewlines",
                            help="split result with space characters")
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server, options.nonewlines)
        string = cnfserver.char.join(cnfserver.variablesCmd(
            options.args, options.mandatory))
        return string


class Data(Runner):

    """ Data runner"""

    #: (:obj:`str`) command description
    description = "get/set values of component variables"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig data \n" \
        + "       nxsconfig data '{\"sample_name\":\"H2O\"}'\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument('args', metavar='name', type=str, nargs='?',
                            help='data dictionary in json string')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server)
        string = cnfserver.char.join(cnfserver.dataCmd(
            options.args))
        return string


class Record(Runner):

    """ Record runner"""

    #: (:obj:`str`) command description
    description = "get a list of datasource record names for " \
                  + "components or datasources"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig record -d exp_mot01 \n" \
        + "       nxsconfig record dcm \n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-d", "--datasources", action="store_true",
                            default=False, dest="datasources",
                            help="perform operation for datasources")
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-n", "--no-newlines", action="store_true",
                            default=False, dest="nonewlines",
                            help="split result with space characters")
        parser.add_argument('args', metavar='name', type=str, nargs='?',
                            help='name of components or datasources')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server, options.nonewlines)
        string = cnfserver.char.join(cnfserver.recordCmd(
            options.datasources, options.args))
        return string


class Servers(Runner):

    """ Servers runner"""

    #: (:obj:`str`) command description
    description = "get a list of configuration servers from" \
                  + " the current tango host"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig servers\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("tango host or configuration server"))
        parser.add_argument("-n", "--no-newlines", action="store_true",
                            default=False, dest="nonewlines",
                            help="split result with space characters")

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        char = " " if options.nonewlines else "\n"
        return char.join(listServers(options.server, 'NXSConfigServer'))


class Describe(Runner):

    """ Describe runner"""

    #: (:obj:`str`) command description
    description = "show all parameters of given components" \
                  + " or datasources"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig describe pilatus\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument(
            "-s", "--server", dest="server",
            help=("configuration server device name"))
        parser.add_argument(
            "-d", "--datasources", action="store_true",
            default=False, dest="datasources",
            help="perform operation for datasources")
        parser.add_argument(
            "-m", "--mandatory", action="store_true",
            default=False, dest="mandatory",
            help="make use mandatory components")
        self._parser.add_argument(
            "-c", "--columns",
            help="names of column to be shown (separated by commas "
            "without spaces). The possible names are: "
            "depends_on, dtype, full_path, nexus_path, nexus_type, shape,"
            " source, source_name, source_type, strategy, trans_type, "
            "trans_offset, trans_vector, units, value",
            dest="headers", default="")
        self._parser.add_argument(
            "-f", "--filters",
            help="filters on the first column (separated by commas "
            "without spaces). Default: '*'. E.g. '*:NXsample/*'",
            dest="filters", default="")
        parser.add_argument(
            "-p", "--private", action="store_true",
            default=False, dest="private",
            help="make use private components,"
            " i.e. starting with '__'")
        parser.add_argument(
            'args', metavar='name', type=str, nargs='*',
            help='names of components or datasources')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server)
        string = cnfserver.char.join(cnfserver.describeCmd(
            options.datasources, options.args, options.mandatory,
            options.private, options.headers, options.filters))
        return string


class Info(Runner):

    """ List runner"""

    #: (:obj:`str`) command description
    description = "show general parameters of given components," \
                  + " datasources or profile"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig info slit1\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-d", "--datasources", action="store_true",
                            default=False, dest="datasources",
                            help="perform operation for datasources")
        parser.add_argument("-r", "--profiles", action="store_true",
                            default=False, dest="profiles",
                            help="perform operation for profiles")
        parser.add_argument("-m", "--mandatory", action="store_true",
                            default=False, dest="mandatory",
                            help="make use mandatory components")
        parser.add_argument("-p", "--private", action="store_true",
                            default=False, dest="private",
                            help="make use private components,"
                            " i.e. starting with '__'")
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components, datasources '
                            'or profiles')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server)
        string = cnfserver.char.join(cnfserver.infoCmd(
            options.datasources, options.args, options.mandatory,
            options.private, options.profiles))
        return string


class Geometry(Runner):

    """ List runner"""

    #: (:obj:`str`) command description
    description = "show transformation parameters of given components" \
                  + " or datasources"
    epilog = "" \
        + " examples:\n" \
        + "       nxsconfig geometry dcm\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        parser = self._parser
        parser.add_argument("-s", "--server", dest="server",
                            help=("configuration server device name"))
        parser.add_argument("-m", "--mandatory", action="store_true",
                            default=False, dest="mandatory",
                            help="make use mandatory components")
        parser.add_argument("-p", "--private", action="store_true",
                            default=False, dest="private",
                            help="make use private components,"
                            " i.e. starting with '__'")
        parser.add_argument('args', metavar='name', type=str, nargs='*',
                            help='names of components or datasources')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        cnfserver = ConfigServer(options.server)
        string = cnfserver.char.join(cnfserver.geometryCmd(
            options.args, options.mandatory,
            options.private))
        return string


def main():
    """ the main program function
    """

    #: pipe arguments
    pipe = []
    if not sys.stdin.isatty():
        #: system pipe
        pipe = sys.stdin.readlines()

    description = "Command-line tool for reading NeXus configuration " \
                  + "from NXSConfigServer"

    epilog = 'For more help:\n  nxsconfig <sub-command> -h'
    parser = NXSArgParser(
        description=description, epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.cmdrunners = [('list', List),
                         ('show', Show),
                         ('get', Get),
                         ('delete', Delete),
                         ('upload', Upload),
                         ('variables', Variables),
                         ('sources', Sources),
                         ('record', Record),
                         ('merge', Merge),
                         ('components', Components),
                         ('data', Data),
                         ('describe', Describe),
                         ('info', Info),
                         ('geometry', Geometry),
                         ('servers', Servers)]
    runners = parser.createSubParsers()
    try:
        options = parser.parse_args()
    except ErrorException as e:
        sys.stderr.write("Error: %s\n" % str(e))
        sys.stderr.flush()
        parser.print_help()
        print("")
        sys.exit(255)

    if hasattr(options, "datasources") and \
       hasattr(options, "profiles") and \
       options.datasources and options.profiles:
        sys.stderr.write(
            "Error: %s\n" % str(
                "argument -d/--datasources and -r/--profiles "
                "cannot be selected simultaneously"))
        sys.stderr.flush()
        parser.print_help()
        print("")
        sys.exit(255)

    if options.subparser is None:
        sys.stderr.write(
            "Error: %s\n" % str("too few arguments"))
        sys.stderr.flush()
        parser.print_help()
        print("")
        sys.exit(255)

    if options.subparser != 'servers':
        if not options.server:
            options.server = checkServer()

        if not options.server:
            print(list(parser.subparsers.keys()))
            parser.subparsers[options.subparser].print_help()
            print("")
            sys.exit(255)

    #: command-line and pipe arguments
    parg = []
    if hasattr(options, "args"):
        if not isinstance(options.args, list):
            options.args = [options.args] if options.args else []
        parg = options.args or []
    if pipe:
        parg.extend([p.strip() for p in pipe])
        if hasattr(options, "args"):
            options.args[:] = parg

    try:
        result = runners[options.subparser].run(options)

        # except tango.DevFailed as
    except Exception as e:
        if isinstance(e, EOFError) \
           and str(e).startswith("EOF when reading a line"):
            sys.stderr.write("Error: %s. Consider to use the "
                             "--force option \n" % str(e))
            sys.stderr.flush()
            sys.exit(255)

        if PYTANGO and isinstance(e, tango.DevFailed):
            # print(str((e.args[0]).desc))
            if str((e.args[0]).desc).startswith(
                    "NonregisteredDBRecordError: The datasource "):
                mydss = str((e.args[0]).desc)[43:].split()
                if not mydss or not mydss[0]:
                    mydss = ["UKNOWN"]
                sys.stderr.write(
                    "Error: Datasource %s not stored in Configuration Server\n"
                    % mydss[0])
                sys.stderr.flush()
            elif str((e.args[0]).desc).startswith(
                    "nxsconfigserver.Errors.NonregisteredDBRecordError:"
                    " The datasource "):
                mydss = str((e.args[0]).desc)[66:].split()
                if not mydss or not mydss[0]:
                    mydss = ["UKNOWN"]
                sys.stderr.write(
                    "Error: Datasource %s not stored in Configuration Server\n"
                    % mydss[0])
                sys.stderr.flush()
            elif str((e.args[0]).desc).startswith(
                    "NonregisteredDBRecordError: Component "):
                mydss = str((e.args[0]).desc)[38:].split()
                if not mydss or not mydss[0]:
                    mydss = ["UKNOWN"]
                sys.stderr.write(
                    "Error: Component %s not stored in Configuration Server\n"
                    % mydss[0])
                sys.stderr.flush()
            elif str((e.args[0]).desc).startswith(
                    "nxsconfigserver.Errors.NonregisteredDBRecordError:"
                    " Component "):
                mydss = str((e.args[0]).desc)[61:].split()
                if not mydss or not mydss[0]:
                    mydss = ["UKNOWN"]
                sys.stderr.write(
                    "Error: Component %s not stored in Configuration Server\n"
                    % mydss[0])
                sys.stderr.flush()
            elif str((e.args[0]).desc).startswith(
                    'IncompatibleNodeError: '):
                sys.stderr.write("Error:%s\n" % (e.args[0]).desc[22:])
                sys.stderr.flush()
            elif str((e.args[0]).desc).startswith(
                    'nxsconfigserver.Errors.IncompatibleNodeError: '):
                sys.stderr.write("Error:%s\n" % (e.args[0]).desc[45:])
                sys.stderr.flush()
            elif str((e.args[0]).desc).startswith(
                    'ExpatError: '):
                sys.stderr.write("Error from XML parser: %s\n"
                                 % (e.args[0]).desc[12:])
                sys.stderr.flush()
            elif str((e.args[0]).desc).startswith(
                    'nxsconfigserver.Errors.ExpatError: '):
                sys.stderr.write("Error from XML parser: %s\n"
                                 % (e.args[0]).desc[35:])
                sys.stderr.flush()
            else:
                sys.stderr.write("Error: %s\n" % str(e))
                sys.stderr.flush()
            sys.exit(255)
        else:
            sys.stderr.write("Error: %s\n" % str(e))
            sys.stderr.flush()
            sys.exit(255)
#        raise
    if result and str(result).strip():
        print(result)


if __name__ == "__main__":
    main()
