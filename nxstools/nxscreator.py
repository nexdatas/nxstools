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

""" Command-line tool for creating to the nexdatas configuration server """

import copy
import os.path
import json
import sys

from operator import itemgetter

import lxml.etree as etree
import xml.etree.ElementTree as et
from lxml.etree import XMLParser

from nxstools.nxsdevicetools import (
    storeDataSource, getDataSourceComponents, storeComponent,
    moduleAttributes, moduleAttributeMap, motorModules,
    generateDeviceNames, getServerTangoHost,
    openServer, findClassName,
    xmlPackageHandler)
from nxstools.nxsxml import (XMLFile, NDSource, NGroup, NField, NLink,
                             NAttr, NDimensions)
from nxstools.pyeval.secop import secop_cmd

#: (:obj:`bool`) True if PyTango available
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
    basestring = str
    unicode = str

npTn = {"double": "NX_FLOAT64",
        "int": "NX_INT64",
        "enum": "NX_INT64",
        "string": "NX_CHAR",
        "bool": "NX_BOOLEAN"}

mnTme = {
    "temperature": "temperature",
    "temperature_regulation": "temperature",
    "magneticfield": "magnetic_field",
    "electricfield": "electric_field",
    "pressure": "pressure",
    "flowrate": "flow",

    # not defined in NeXus yet
    # "humidity": "humidity",
    # "viscosity": "viscosity",
    # "concentration": "concentration",
    # "rotation_z": "rotation_z",

    # not defined in secop yet
    "ph": "pH",
    "conductivity": "conductivity",
    "resistance": "resistance",
    "voltage": "voltage",
    "surfacepressure": "surface_pressure",
    "stress": "stress",
    "strain": "strain",
    "shear": "shear",
  }


class CPExistsException(Exception):

    """ Component already exists exception
    """


class DSExistsException(Exception):

    """ DataSource already exists exception
    """


def _tostr(text):
    """ converts text  to str type

    :param text: text
    :type text: :obj:`bytes` or :obj:`unicode`
    :returns: text in str type
    :rtype: :obj:`str`
    """
    if hasattr(text, "tostring"):
        text = text.tostring()
    if isinstance(text, str):
        return text
    elif sys.version_info > (3,):
        return str(text, encoding="utf-8")
    else:
        return str(text)


def _toxml(node):
    """ provides xml content of the whole node

    :param node: DOM node
    :type node: :class:`xml.dom.Node`
    :returns: xml content string
    :rtype: :obj:`str`
    """
    if sys.version_info > (3,):
        xml = _tostr(et.tostring(node, encoding='unicode', method='xml'))
    else:
        xml = _tostr(et.tostring(node, encoding='utf8', method='xml'))
    if xml.startswith("<?xml version='1.0' encoding='utf-8'?>"):
        xml = str(xml[39:])
    elif xml.startswith("<?xml version='1.0' encoding='utf8'?>"):
        xml = str(xml[38:])
    return xml


def _simpletoxml(node):
    """ provides xml content of the whole node

    :param node: DOM node
    :type node: :class:`xml.dom.Node`
    :returns: xml content string
    :rtype: :obj:`str`
    """
    if sys.version_info > (3,):
        return _tostr(et.tostring(node, encoding='unicode', method='xml'))
    else:
        return _tostr(et.tostring(node, encoding='utf8', method='xml'))


class Device(object):

    """ device from online.xml
    """
    __slots__ = [
        'name', 'dtype', 'module', 'tdevice', 'sdevice',
        'hostname', 'sardananame', 'sardanahostname',
        'host', 'port', 'shost', 'sport', 'thost', 'tport',
        'group', 'attribute']

    def __init__(self):
        #: (:obj:`str`) device name
        self.name = None
        #: (:obj:`str`) device type
        self.dtype = None
        #: (:obj:`str`) device module
        self.module = None
        #: (:obj:`str`) tango device name
        self.tdevice = None
        #: (:obj:`str`) sardana device name
        self.sdevice = None
        #: (:obj:`str`) host name with port
        self.hostname = None
        #: (:obj:`str`) sardana name with port
        self.sardananame = None
        #: (:obj:`str`) sardana host name
        self.sardanahostname = None
        #: (:obj:`str`) host without port
        self.host = None
        #: (:obj:`str`) port
        self.port = None
        #: (:obj:`str`) tango host without port
        self.thost = None
        #: (:obj:`str`) tango port
        self.tport = None
        #: (:obj:`str`) sardana host without port
        self.shost = None
        #: (:obj:`str`) sardana tango port
        self.sport = None
        #: (:obj:`str`) datasource tango group
        self.group = None
        #: (:obj:`str`) attribute name
        self.attribute = None

    def compare(self, dv):
        dct = {}
        tocompare = [
            "name", "dtype", "module", "tdevice", "hostname",
            "sardananame", "sardanahostname"]
        for at in tocompare:
            v1 = getattr(self, at)
            v2 = getattr(dv, at)
            if v1 != v2:
                dct[at] = (str(v1) if v1 else v1, str(v2) if v2 else v2)
        return dct

    def tolower(self):
        """ converts `name`, `module`, `tdevice`, `hostname` into lower case
        """
        if self.name:
            self.name = self.name.lower()
        if self.module:
            self.module = self.module.lower()
        if self.tdevice:
            self.tdevice = self.tdevice.lower()
        if self.hostname:
            self.hostname = self.hostname.lower()

    def splitHostPort(self):
        """ spilts host name from port
        """
        if self.hostname:
            self.host = self.hostname.split(":")[0]
            self.port = self.hostname.split(":")[1] \
                if len(self.hostname.split(":")) > 1 else None
            self.thost = self.host
            self.tport = self.port
        else:
            self.host = None
            self.port = None
            raise Exception("hostname not defined")

    def findDevice(self, tangohost):
        """ sets sardana device name and sardana host/port of online.xml device

        :param tangohost: tango host
        :type tangohost: :obj:`str`
        """
        mhost = self.sardanahostname or tangohost
        self.sdevice = None
        self.shost = None
        self.sport = None
        if PYTANGO:
            try:
                dp = tango.DeviceProxy(str("%s/%s" % (mhost, self.name)))
                mdevice = str(dp.name())

                #  self.hostname = mhost
                self.shost = mhost.split(":")[0]
                if len(mhost.split(":")) > 1:
                    self.sport = mhost.split(":")[1]

                self.sdevice = mdevice
            except Exception:
                pass

    def findAttribute(self, tangohost, clientlike=False):
        """ sets attribute and datasource group of online.xml device

        :param tangohost: tango host
        :type tangohost: :obj:`str`
        :param clientlike: tango motors to be client like
        :type clientlike: :obj:`bool`
        """
        mhost = self.sardanahostname or tangohost
        self.group = None
        self.attribute = None
        spdevice = self.tdevice.split("/")
        if mhost and len(spdevice) > 3:
            self.tdevice = "/".join(spdevice[0:3])
            self.hostname = mhost
            if self.module in moduleAttributeMap.keys() and \
                    spdevice[3] in moduleAttributeMap[self.module].keys():
                self.attribute = moduleAttributeMap[self.module][spdevice[3]]
            else:
                self.attribute = spdevice[3]
        if self.module in motorModules or self.dtype == 'stepping_motor':
            if self.attribute is None:
                self.attribute = 'Position'
            if clientlike:
                self.group = '__CLIENT__'
        elif PYTANGO and self.module in moduleAttributes:
            try:
                try:
                    dp = tango.DeviceProxy(
                        str("%s/%s" % (mhost, self.sardananame)))
                except Exception:
                    dp = tango.DeviceProxy(str("%s/%s" % (mhost, self.name)))
                mdevice = str(dp.name())

                sarattr = moduleAttributes[self.module][0]
                if not sarattr or \
                   sarattr not in dp.get_attribute_list():
                    raise Exception("Missing attribute: Value")
                self.hostname = mhost
                self.host = mhost.split(":")[0]
                self.shost = self.host
                if len(mhost.split(":")) > 1:
                    self.port = mhost.split(":")[1]
                    self.sport = self.port
                if mdevice:
                    self.sdevice = mdevice
                self.attribute = sarattr
                self.group = '__CLIENT__'
            except Exception:
                if moduleAttributes[self.module][1]:
                    if self.attribute is None:
                        self.attribute = moduleAttributes[self.module][1]
                    self.group = '__CLIENT__'

    def setSardanaName(self, tolower):
        """ sets sardana name

        :param tolower: If True name in lowercase
        :type tolower: :obj:`bool`
        """
        self.name = self.sardananame or self.name
        if tolower:
            self.name = self.name.lower()


class Creator(object):

    """ configuration server adapter
    """

    def __init__(self, options, args, printouts=True):
        """ constructor

        :param options:  command options
        :type options: :class:`optparse.Values`
        :param args: command arguments
        :type args: :obj:`list` < :obj:`str` >
        :param printouts: if printout is enable
        :type printouts: :obj:`bool`
        """
        #: (:class:`optparse.Values`) creator options
        self.options = options
        #: (:obj:`list` < :obj:`str` >) creator arguments
        self.args = args
        #: (:obj:`bool`) if printout is enable
        self._printouts = printouts

    @classmethod
    def _areComponentsAvailable(cls, names, server, lower=False):
        """ checks if the components are available

        :param names: component names
        :type names: :obj:`list` < :obj:`str` >
        :param server: server name
        :type server: :obj:`str`
        :param lower: checks lower case name
        :type lower: :obj:`bool`
        :returns: a subset of available components
        :rtype:  :obj:`list` < :obj:`str` >
        """
        try:
            proxy = openServer(server)
            proxy.Open()
            acps = proxy.availableComponents()
        except Exception:
            raise Exception("Cannot connect to %s" % server)
        cps = []
        for name in names:
            if name in acps or (lower and name.lower() in acps):
                cps.append(name)
        return cps

    @classmethod
    def _componentFilesExist(cls, names, fileprefix, directory):
        """ checks if the components files exist

        :param names: component names
        :type names: :obj:`list` < :obj:`str` >
        :param fileprefix: file name prefix
        :type fileprefix: :obj:`str`
        :param directory: file directory
        :type directory: :obj:`str`
        :param lower: checks lower case name
        :type lower: :obj:`bool`
        :returns: a subset of available components
        :rtype:  :obj:`list` < :obj:`str` >
        """
        cps = []
        for name in names:
            fname = "%s/%s%s.xml" % (directory, fileprefix, name)
            if os.path.exists(fname):
                cps.append(fname)
        return cps

    @classmethod
    def _areDataSourcesAvailable(cls, names, server, lower=False):
        """ checks if the datasources are available

        :param names: datasource names
        :type names: :obj:`list` < :obj:`str` >
        :param server: server name
        :type server: :obj:`str`
        :param lower: checks lower case name
        :type lower: :obj:`bool`
        :returns: a subset of available datasources
        :rtype:  :obj:`list` < :obj:`str` >
        """
        try:
            proxy = openServer(server)
            proxy.Open()
            adss = proxy.availableDataSources()
        except Exception:
            raise Exception("Cannot connect to %s" % server)
        dss = []
        for name in names:
            if name in adss or (lower and name.lower() in adss):
                dss.append(name)
        return dss

    @classmethod
    def _dataSourceFilesExist(cls, names, fileprefix, directory):
        """ checks if the datasources files exist

        :param names: datasource names
        :type names: :obj:`list` < :obj:`str` >
        :param fileprefix: file name prefix
        :type fileprefix: :obj:`str`
        :param directory: file directory
        :type directory: :obj:`str`
        :param lower: checks lower case name
        :type lower: :obj:`bool`
        :returns: a subset of available datasources
        :rtype:  :obj:`list` < :obj:`str` >
        """
        dss = []
        for name in names:
            fname = "%s/%s%s.ds.xml" % (directory, fileprefix, name)
            if os.path.exists(fname):
                dss.append(fname)
        return dss

    @classmethod
    def _createTangoDataSource(
            cls, name, directory, fileprefix, server, device,
            elementname, host, port="10000", group=None, elementtype=None):
        """ creates TANGO datasource file

        :param name: device name
        :type name: :obj:`str`
        :param directory: output file directory
        :type directory: :obj:`str`
        :param fileprefix: file name prefix
        :type fileprefix: :obj:`str`
        :param server: server name
        :type server: :obj:`str`
        :param device: device name
        :type device: :obj:`str`
        :param elementname: element name, e.g. attribute name
        :type elementname: :obj:`str`
        :param host: tango host name
        :type host: :obj:`str`
        :param port: tango port
        :type port: :obj:`str`
        :parma group: datasource tango group
        :type group: :obj:`str`
        :parma elementtype: element type, i.e. attribute, property or command
        :type elementtype: :obj:`str`
        :returns: xml string
        :rtype: :obj:`str`
        """
        df = XMLFile("%s/%s%s.ds.xml" % (directory, fileprefix, name))
        sr = NDSource(df)
        sr.initTango(name, device, elementtype or "attribute",
                     elementname, host, port, group=group)
        xml = df.prettyPrint()
        if server:
            storeDataSource(name, xml, server)
        elif directory is not None and fileprefix is not None:
            df.dump()
        return xml

    @classmethod
    def _createClientDataSource(
            cls, name, directory, fileprefix, server, dsname=None):
        """ creates CLIENT datasource file

        :param name: device name
        :type name: :obj:`str`
        :param directory: output file directory
        :type directory: :obj:`str`
        :param fileprefix: file name prefix
        :type fileprefix: :obj:`str`
        :param server: server name
        :type server: :obj:`str`
        :param dsname: datasource name
        :type dsname: :obj:`str`
        :returns: xml string
        :rtype: :obj:`str`
        """
        dname = name if not dsname else dsname
        df = XMLFile("%s/%s%s.ds.xml" % (directory, fileprefix, dname))
        print("%s/%s%s.ds.xml" % (directory, fileprefix, dname))
        sr = NDSource(df)
        sr.initClient(dname, name)
        xml = df.prettyPrint()
        if server:
            storeDataSource(dname, xml, server)
        elif directory is not None and fileprefix is not None:
            df.dump()
        return xml

    @classmethod
    def __patheval(cls, nexuspath):
        """ splits nexus path into list

        :param nexuspath: nexus path
        :type nexuspath: :obj:`str`
        :returns: nexus path in lists of (name, NXtype)
        :rtype: :obj:`list` < (:obj:`str`, :obj:`str`) >
        """
        pathlist = []
        spath = nexuspath.split("/")
        if spath:
            for sp in spath[:-1]:
                nlist = sp.split(":")
                if len(nlist) == 2:
                    if len(nlist[0]) == 0 and \
                       len(nlist[1]) > 2 and nlist[1].startswith("NX"):
                        pathlist.append((nlist[1][2:], nlist[1]))
                    else:
                        pathlist.append((nlist[0], nlist[1]))
                elif len(nlist) == 1 and nlist[0]:
                    if len(nlist[0]) > 2 and nlist[0].startswith("NX"):
                        pathlist.append((nlist[0][2:], nlist[0]))
                    else:
                        pathlist.append((nlist[0], "NX" + nlist[0]))

            pathlist.append((spath[-1], None))
        return pathlist

    @classmethod
    def __createTree(cls, df, nexuspath, name, nexusType,
                     strategy, units, link, chunk, canfail=None,
                     depends=None):
        """ create nexus node tree

        :param df: definition parent node
        :type df: :class:'nxstools.nxsxml.XMLFile'
        :param nexuspath: nexus path
        :type nexuspath: :obj:`str`
        :param name: name
        :type name: :obj:`str`
        :param nexusType: nexus type
        :type nexusType: :obj:`str`
        :param strategy: strategy mode
        :type startegy: :obj:`str`
        :param units: field units
        :type units: :obj:`str`
        :param links: if create link
        :type links: :obj:`bool`
        :param chunk: chunk size, e.g. `SCALAR`, `SPECTRUM` or `IMAGE`
        :type chunk: :obj:`str`
        :param canfail: can fail strategy flag
        :type canfail: :obj:`bool`
        :param depends: a list of component dependencies separated by ','
        :type depends: :obj:`str`
        """

        pathlist = cls.__patheval(nexuspath)
        entry = None
        parent = df
        for path in pathlist[:-1]:
            child = NGroup(parent, path[0], path[1])
            if parent == df:
                entry = child
            parent = child
        if pathlist:
            fname = pathlist[-1][0] or name
            field = NField(parent, fname, nexusType)
            field.setStrategy(strategy, canfail=canfail)
            if units.strip():
                field.setUnits(units.strip())
            field.setText("$datasources.%s" % name)
            if chunk != 'SCALAR':
                if chunk == 'SPECTRUM':
                    NDimensions(field, "1")
                elif chunk == 'IMAGE':
                    NDimensions(field, "2")
            if link and entry:
                npath = (nexuspath + name) \
                    if nexuspath[-1] == '/' else nexuspath
                data = NGroup(entry, "data", "NXdata")
                if link > 1:
                    NLink(data, name, npath)
                else:
                    NLink(data, fname, npath)
        if depends:
            deps = [dp for dp in depends.split(",") if dp]
            if deps:
                df.setDependencies(deps, entry)

    @classmethod
    def _createComponent(cls, name, directory, fileprefix, nexuspath,
                         strategy, nexusType, units, links, server, chunk,
                         dsname, canfail=None, depends=None):
        """ creates component file

        :param name: component name
        :type name: :obj:`str`
        :param directory: output file directory
        :type directory: :obj:`str`
        :param fileprefix: file name prefix
        :type fileprefix: :obj:`str`
        :param nexuspath: nexus path
        :type nexuspath: :obj:`str`
        :param strategy: field strategy
        :type startegy: :obj:`str`
        :param nexusType: nexus Type of the field
        :type nexusType: :obj:`str`
        :param units: field units
        :type units: :obj:`str`
        :param link: nxdata link
        :type links: :obj:`bool`
        :param server: configuration server
        :type server: :obj:`str`
        :returns: component xml
        :rtype: :obj:`str`
        :param dsname: datasource name
        :type dsname: :obj:`str`
        :param canfail: can fail strategy flag
        :type canfail: :obj:`bool`
        :param depends: a list of component dependencies separated by ','
        :type depends: :obj:`str`
        """
        defpath = "/$var.entryname#'scan'$var.serialno:NXentry/instrument" \
                  + "/collection/%s" % (dsname or name)
        df = XMLFile("%s/%s%s.xml" % (directory, fileprefix, name))
        cls.__createTree(df, nexuspath or defpath, dsname or name, nexusType,
                         strategy, units, links, chunk, canfail, depends)

        xml = df.prettyPrint()
        if server:
            storeComponent(name, xml, server)
        elif directory is not None and fileprefix is not None:
            df.dump()
        return xml

    @classmethod
    def _getText(cls, node):
        """ provides xml content of the node

        :param node: DOM node
        :type node: :class:`lxml.etree.Element`
        :returns: xml content string
        :rtype: :obj:`str`
        """
        if node is None:
            return
        xml = _toxml(node)
        start = xml.find('>')
        end = xml.rfind('<')
        if start == -1 or end < start:
            return ""
        return xml[start + 1:end].replace("&lt;", "<").replace("&gt;", "<"). \
            replace("&quot;", "\"").replace("&amp;", "&")

    @classmethod
    def _getChildText(cls, parent, childname):
        """ provides text of child named by childname

        :param parent: parent node
        :type parent: :class:`lxml.etree.Element`
        :param childname: child name
        :type childname: :opj:`str`
        :returns: text string
        :rtype: :obj:`str`
        """
        children = parent.findall(childname)
        return cls._getText(children[0]) if len(children) else None

    def _getModuleName(self, device):
        """ provides module name

        :param device: device name
        :type device: :obj:`str`
        :returns: module name
        :rtype: :obj:`str`
        """
        if device.module.lower() in \
           self.xmlpackage.moduleMultiAttributes.keys():
            return device.module.lower()
        elif len(device.tdevice.split('/')) == 3:
            try:
                classname = findClassName(device.hostname, device.tdevice)
                if classname.lower() \
                   in self.xmlpackage.moduleMultiAttributes.keys():
                    return classname.lower()
            except Exception:
                pass
            if device.module.lower() == 'module_tango' \
               and len(device.tdevice.split('/')) == 3 \
               and device.tdevice.split('/')[1] \
               in self.xmlpackage.moduleMultiAttributes.keys():
                return device.tdevice.split('/')[1].lower()


class WrongParameterError(Exception):

    """ wrong parameter exception
    """
    pass


class ComponentCreator(Creator):

    """ component creator
    """

    def create(self):
        """ creates a component xml and stores it in DB or filesytem
        """
        aargs = []
        if self.options.device.strip():
            try:
                first = int(self.options.first)
            except Exception:
                raise WrongParameterError(
                    "ComponentCreator Invalid --first parameter\n")

            try:
                last = int(self.options.last)
            except Exception:
                raise WrongParameterError(
                    "ComponentCreator Invalid --last parameter\n")
            aargs = generateDeviceNames(self.options.device, first, last,
                                        self.options.minimal)
            if self.options.datasource:
                dsargs = generateDeviceNames(
                    self.options.datasource, first, last,
                    self.options.minimal) or None
            else:
                dsargs = None
        else:
            dsargs = None

        self.args += aargs
        if not len(self.args):
            raise WrongParameterError("")

        if dsargs is None and self.options.datasource:
            dsargs = [self.options.datasource]
        if dsargs is not None and len(self.args) != len(dsargs):
            raise WrongParameterError(
                "component names cannot be match into datasource namse")
        if self.options.database:
            if not self.options.overwrite:
                existing = self._areComponentsAvailable(
                    self.args, self.options.server)
                if existing:
                    raise CPExistsException(
                        "Components '%s' already exist." % existing)
        elif not self.options.overwrite:
            existing = self._componentFilesExist(
                self.args, self.options.file, self.options.directory)
            if existing:
                raise CPExistsException(
                    "Component files '%s' already exist." % existing)

        for i, name in enumerate(self.args):
            dsname = dsargs[i] if dsargs is not None else None
            if not self.options.database:
                if self._printouts:
                    print("CREATING: %s%s.xml" % (self.options.file, name))
            else:
                if self._printouts:
                    print("STORING: %s" % (name))
            self._createComponent(
                name, self.options.directory,
                self.options.file,
                self.options.nexuspath,
                self.options.strategy,
                self.options.type,
                self.options.units,
                int(self.options.fieldlinks) + 2 * int(
                    self.options.sourcelinks),
                self.options.server if self.options.database else None,
                self.options.chunk, dsname,
                self.options.canfail,
                self.options.depends
            )


class TangoDSCreator(Creator):

    """ tango datasource creator
    """

    def create(self):
        """ creates a tango datasource xml and stores it in DB or filesytem
        """
        dvargs = []
        dsargs = []
        if self.options.device.strip():
            try:
                last = int(self.options.last)
                try:
                    first = int(self.options.first)
                except Exception:
                    first = 1
                dvargs = generateDeviceNames(
                    self.options.device, first, last)
                dsargs = generateDeviceNames(
                    self.options.datasource, first, last)
            except Exception:
                dvargs = [str(self.options.device)]
                dsargs = [str(self.options.datasource)]

        if not dvargs or not len(dvargs):
            raise WrongParameterError("")

        if self.options.database:
            if not self.options.overwrite:
                existing = self._areDataSourcesAvailable(
                    dsargs, self.options.server)
                if existing:
                    raise DSExistsException(
                        "DataSources '%s' already exist." % existing)
        elif not self.options.overwrite:
            existing = self._dataSourceFilesExist(
                dsargs, self.options.file, self.options.directory)
            if existing:
                raise DSExistsException(
                    "DataSource files '%s' already exist." % existing)

        for i in range(len(dvargs)):
            if not self.options.database:
                print("CREATING %s: %s%s.ds.xml" % (
                    dvargs[i], self.options.file, dsargs[i]))
            else:
                print("STORING %s: %s" % (dvargs[i], dsargs[i]))
            self._createTangoDataSource(
                dsargs[i], self.options.directory, self.options.file,
                self.options.server if self.options.database else None,
                dvargs[i],
                self.options.attribute,
                self.options.host,
                self.options.port,
                self.options.group or None,
                self.options.elementtype or "attribute"
            )


class ClientDSCreator(Creator):

    """ client datasource creator
    """

    def create(self):
        """ creates a client datasource xml and stores it in DB or filesytem
        """
        dsargs = None
        aargs = []
        if self.options.device.strip():
            try:
                first = int(self.options.first)
            except Exception:
                raise WrongParameterError(
                    "ClientDSCreator: Invalid --first parameter\n")
            try:
                last = int(self.options.last)
            except Exception:
                raise WrongParameterError(
                    "ClientDSCreator: Invalid --last parameter\n")

            aargs = generateDeviceNames(self.options.device, first, last,
                                        self.options.minimal)
            if self.options.dsource:
                dsaargs = generateDeviceNames(
                    self.options.dsource, first, last)
                dsargs = list(self.args) + dsaargs

        self.args += aargs
        if not dsargs:
            dsargs = self.args
        if not len(self.args):
            raise WrongParameterError("")

        if self.options.database:
            if not self.options.overwrite:
                existing = self._areDataSourcesAvailable(
                    dsargs, self.options.server)
                if existing:
                    raise DSExistsException(
                        "DataSources '%s' already exist." % existing)
        elif not self.options.overwrite:
            existing = self._dataSourceFilesExist(
                dsargs, self.options.file, self.options.directory)
            if existing:
                raise DSExistsException(
                    "DataSource files '%s' already exist." % existing)

        for i in range(len(self.args)):
            if not self.options.database:
                print("CREATING: %s%s.ds.xml" % (
                    self.options.file, dsargs[i]))
            else:
                print("STORING: %s" % (dsargs[i]))
            self._createClientDataSource(
                self.args[i], self.options.directory,
                self.options.file,
                self.options.server if self.options.database else None,
                dsargs[i])


class DeviceDSCreator(Creator):

    """ device datasource creator
    """

    def create(self):
        """ creates a tango datasources xml of given device
            and stores it in DB or filesytem
        """
        if self.options.database:
            if not self.options.overwrite:
                dsargs = [
                    "%s%s" % (self.options.datasource.lower(), at.lower())
                    for at in self.args
                ]
                existing = self._areDataSourcesAvailable(
                    dsargs, self.options.server)
                if existing:
                    raise DSExistsException(
                        "DataSources '%s' already exist." % existing)
        elif not self.options.overwrite:
            dsargs = [
                "%s%s" % (self.options.datasource.lower(), at.lower())
                for at in self.args
            ]
            existing = self._dataSourceFilesExist(
                dsargs, self.options.file, self.options.directory)
            if existing:
                raise DSExistsException(
                    "DataSource files '%s' already exist." % existing)

        for at in self.args:
            dsname = "%s%s" % (self.options.datasource.lower(), at.lower())
            if not self.options.database:
                if self._printouts:
                    print("CREATING %s/%s: %s%s.ds.xml" % (
                        self.options.device, at, self.options.file, dsname))
            else:
                if self._printouts:
                    print("STORING %s/%s: %s" % (
                        self.options.device, at, dsname))
            self._createTangoDataSource(
                dsname, self.options.directory, self.options.file,
                self.options.server if self.options.database else None,
                self.options.device, at, self.options.host,
                self.options.port,
                self.options.datasource
                if not self.options.nogroup else None)


class PoolDSCreator(Creator):

    """ datasource creator of all sardana pool acquisition channels
    """

    def __init__(self, options, args, printouts=True):
        """ constructor

        :param options: command options
        :type options: :class:`optparse.Values`
        :param args: command arguments
        :type args: :obj:`list` <:obj:`str` >
        :param printouts: if printout is enable
        :type printouts: :obj:`bool`
        """
        Creator.__init__(self, options, args, printouts)
        #: (:obj:`dict` <:obj:`str`, :obj:`str` >) datasource xml dictionary
        self.datasources = {}

    def _printAction(self, dv, dscps=None):
        """ prints out information about the performed action

        :param dv: online device object
        :type dv: :class:`Device`
        :param dscps: datasource components
        :type dscps: :obj:`dict` <:obj:`str`, :obj:`list` < :obj:`str` > >
        """
        if self._printouts:
            if hasattr(self.options, "directory") and \
               self.options.directory:
                print("CREATING %s: %s/%s%s.ds.xml" % (
                    dv.tdevice, self.options.directory,
                    self.options.file, dv.name))
            elif self.options.database:
                print("CREATING %s %s/%s/%s %s" % (
                    str(dv.name) + ":" + " " * (34 - len(dv.name or "")),
                    dv.hostname,
                    dv.tdevice,
                    str(dv.attribute) + " " * (
                        70 - len(dv.tdevice or "") - len(dv.attribute or "")
                        - len(dv.hostname or "")),
                    ",".join(dscps[dv.name])
                    if (dscps and dv.name in dscps and dscps[dv.name])
                    else ""))
            else:
                print("TEST %s %s/%s/%s %s" % (
                    str(dv.name) + ":" + " " * (34 - len(dv.name or "")),
                    dv.hostname,
                    dv.tdevice,
                    str(dv.attribute) + " " * (
                        70 - len(dv.tdevice or "") - len(dv.attribute or "")
                        - len(dv.hostname or "")),
                    ",".join(dscps[dv.name])
                    if (dscps and dv.name in dscps and dscps[dv.name])
                    else ""))

    def create(self):
        """ creates datasources of all online.xml simple devices
        """
        self.createXMLs()
        server = self.options.server
        if not hasattr(self.options, "directory") or \
           not self.options.directory:
            if self.options.database:
                for dsname, dsxml in self.datasources.items():
                    storeDataSource(dsname, dsxml, server)
        else:
            for dsname, dsxml in self.datasources.items():
                with open("%s/%s%s.ds.xml" % (
                        self.options.directory,
                        self.options.file, dsname), "w") as myfile:
                    myfile.write(dsxml)

    def __createDevice(self, name, source, clientlike=True):
        """  create Device from name source and chtype

        :param name: alias device name
        :type name: :obj:`str`
        :param source: device source string
        :type source: :obj:`str`
        :param clientlike: device to be client like
        :type clientlike: :obj:`bool`
        :returns: device object
        :rtype: :obj:`Device`
        """
        dv = Device()
        if name and source:
            if source.startswith("tango://"):
                source = source[8:]
            slst = source.split('/')
            if not slst[0] or ":" not in slst[0] or len(slst) < 2:
                return dv
            hplst = slst[0].split(":")
            if len(hplst) != 2:
                return dv
            dv.host, dv.port = hplst[0], hplst[1]
            dv.hostname = slst[0]
            dv.attribute = slst[-1]
            dv.name = name
            dv.tdevice = "/".join(slst[1:-1])
            if clientlike:
                dv.group = "__CLIENT__"
        return dv

    def createXMLs(self):
        """ creates datasource xmls of all online.xml simple devices
        """
        self.datasources = {}
        plname = self.options.pool
        motors = ['Motor', 'PseudoMotor']
        expchnls = ['CTExpChannel', 'ZeroDExpChannel',
                    'OneDExpChannel', 'TwoDExpChannel',
                    'PseudoCounter']
        if 'ALL' in self.args or not self.args:
            args = list(motors)
            args.extend(expchnls)
        else:
            args = list(self.args)
        try:
            plproxy = openServer(plname)
        except Exception:
            raise Exception("Cannot connect to %s" % plname)
        try:
            chlist = plproxy.ExpChannelList
        except Exception:
            chlist = []
        try:
            motorlist = plproxy.MotorList
        except Exception:
            motorlist = []
        for ellist in [chlist, motorlist]:
            for els in ellist:
                elprop = json.loads(els) or {}
                if 'name' in elprop.keys() \
                   and 'source' in elprop.keys() \
                   and 'type' in elprop.keys():
                    if elprop['name'] in args or elprop['type'] in args:
                        dv = self.__createDevice(
                            elprop['name'], elprop['source'],
                            self.options.clientlike)
                        if self.options.lower:
                            dv.tolower()
                        if dv.tdevice and dv.attribute and dv.host and dv.port:
                            self._printAction(dv)
                            xml = self._createTangoDataSource(
                                dv.name, None, None, None,
                                dv.tdevice, dv.attribute, dv.host,
                                dv.port, dv.group)
                            self.datasources[dv.name] = xml


class OnlineDSCreator(Creator):

    """ datasource creator of all online.xml simple devices
    """

    def __init__(self, options, args, printouts=True):
        """ constructor

        :param options: command options
        :type options: :class:`optparse.Values`
        :param args: command arguments
        :type args: :obj:`list` <:obj:`str` >
        :param printouts: if printout is enable
        :type printouts: :obj:`bool`
        """
        Creator.__init__(self, options, args, printouts)
        #: (:obj:`dict` <:obj:`str`, :obj:`str` >) datasource xml dictionary
        self.datasources = {}
        if options.xmlpackage:
            xmlPackageHandler.loadXMLTemplates(options.xmlpackage)
        else:
            xmlPackageHandler.loadXMLTemplates('nxstools.xmltemplates')
        #: (:obj:`str`) xml template component package path
        self.xmltemplatepath = xmlPackageHandler.packagepath
        #: (:obj:`str`) xml template component package
        self.xmlpackage = xmlPackageHandler.package

    def _printAction(self, dv, dscps=None):
        """ prints out information about the performed action

        :param dv: online device object
        :type dv: :class:`Device`
        :param dscps: datasource components
        :type dscps: :obj:`dict` <:obj:`str`, :obj:`list` < :obj:`str` > >
        """
        if self._printouts:
            if hasattr(self.options, "directory") and \
               self.options.directory:
                print("CREATING %s: %s/%s%s.ds.xml" % (
                    dv.tdevice, self.options.directory,
                    self.options.file, dv.name))
            elif self.options.database:
                print("CREATING %s %s/%s/%s %s" % (
                    str(dv.name) + ":" + " " * (34 - len(dv.name or "")),
                    dv.hostname,
                    dv.tdevice,
                    str(dv.attribute) + " " * (
                        70 - len(dv.tdevice or "") - len(dv.attribute or "")
                        - len(dv.hostname or "")),
                    ",".join(dscps[dv.name])
                    if (dscps and dv.name in dscps and dscps[dv.name])
                    else ""))
            else:
                print("TEST %s %s %s %s/%s/%s %s" % (
                    str(dv.name) + ":" + " " * (34 - len(dv.name or "")),
                    str(dv.dtype) + ":" + " " * (20 - len(dv.dtype or "")),
                    str(dv.module) + ":" + " " * (24 - len(dv.module or "")),
                    dv.hostname,
                    dv.tdevice,
                    str(dv.attribute) + " " * (
                        70 - len(dv.tdevice or "") - len(dv.attribute or "")
                        - len(dv.hostname or "")),
                    ",".join(dscps[dv.name])
                    if (dscps and dv.name in dscps and dscps[dv.name])
                    else ""))

    def create(self):
        """ creates datasources of all online.xml simple devices
        """
        self.createXMLs()
        server = self.options.server
        if not hasattr(self.options, "directory") or \
           not self.options.directory:
            if self.options.database:
                for dsname, dsxml in self.datasources.items():
                    storeDataSource(dsname, dsxml, server)
        else:
            for dsname, dsxml in self.datasources.items():
                with open("%s/%s%s.ds.xml" % (
                        self.options.directory,
                        self.options.file, dsname), "w") as myfile:
                    myfile.write(dsxml)

    def createXMLs(self):
        """ creates datasource xmls of all online.xml simple devices
        """
        self.datasources = {}
        tangohost = getServerTangoHost(
            self.options.external or self.options.server)
        hw = etree.parse(self.args[0],
                         parser=XMLParser(collect_ids=False)).getroot()
        if hw.tag != 'hw':
            hw = hw.find('hw')
        dscps = {}
        if self.options.server and self._printouts and \
           (
               not hasattr(self.options, "directory") or
               not self.options.directory
           ):
            try:
                dscps = getDataSourceComponents(
                    self.options.server, self.options.verbose)
            except Exception:
                dscps = {}

        for device in hw:
            if device.tag == 'device':
                dv = Device()
                dv.name = self._getChildText(device, "name")
                dv.dtype = self._getChildText(device, "type")
                dv.module = self._getChildText(device, "module")
                dv.tdevice = self._getChildText(device, "device")
                dv.hostname = self._getChildText(device, "hostname")
                dv.sardananame = self._getChildText(device, "sardananame")
                dv.sardanahostname = self._getChildText(
                    device, "sardanahostname")
                if self.options.lower:
                    dv.tolower()
                try:
                    dv.splitHostPort()
                except Exception:
                    if self._printouts:
                        print("ERROR %s: host for module %s of %s "
                              "type not defined"
                              % (dv.name, dv.module, dv.dtype))
                    continue
                dv.findAttribute(tangohost, self.options.clientlike)
                created = False
                if dv.attribute:
                    dv.setSardanaName(self.options.lower)
                    mdv = copy.copy(dv)
                    mdv.tdevice = dv.sdevice or dv.tdevice
                    self._printAction(mdv, dscps)
                    xml = self._createTangoDataSource(
                        mdv.name, None, None, None,
                        mdv.tdevice, mdv.attribute, mdv.host,
                        mdv.port, mdv.group)
                    self.datasources[mdv.name] = xml
                    created = True
                module = self._getModuleName(dv)
                smodule = "%s@pool" % module.lower() if module else None
                if module and module.lower() in \
                   self.xmlpackage.moduleMultiAttributes.keys():
                    multattr = self.xmlpackage.moduleMultiAttributes[
                        module.lower()]
                    for at in multattr:
                        dsname = "%s_%s" % (dv.name.lower(), at.lower())
                        xml = self._createTangoDataSource(
                            dsname, None, None, None,
                            dv.tdevice, at, dv.thost, dv.tport,
                            "%s_" % (dv.name))
                        self.datasources[dsname] = xml
                        mdv = copy.copy(dv)
                        mdv.name = dsname
                        mdv.hostname = "%s:%s" % (dv.thost, dv.tport)
                        mdv.attribute = at
                        self._printAction(mdv, dscps)
                    created = True
                if smodule in \
                   self.xmlpackage.moduleMultiAttributes.keys():
                    smultattr = self.xmlpackage.moduleMultiAttributes[
                        smodule]
                    if smultattr and not dv.sdevice:
                        if self._printouts:
                            print(
                                "SKIPPING %s: Device cannot be found" %
                                dv.name)
                    else:
                        for at in smultattr:
                            dsname = "%s_%s" % (
                                dv.name, at.lower())
                            xml = self._createTangoDataSource(
                                dsname, None, None, None,
                                dv.sdevice, at, dv.shost, dv.sport,
                                "%s_" % (dv.name))
                            #   "__CLIENT__")
                            self.datasources[dsname] = xml
                            mdv = copy.copy(dv)
                            mdv.name = dsname
                            mdv.tdevice = dv.sdevice
                            mdv.hostname = "%s:%s" % (dv.shost, dv.sport)
                            mdv.attribute = at
                            self._printAction(mdv, dscps)
                        created = True
                if not created:
                    if self._printouts:
                        print(
                            "SKIPPING %s:    module '%s' of '%s' "
                            "type not defined"
                            % (dv.name, dv.module, dv.dtype))


class CPCreator(Creator):

    """ component creator of all online.xml complex devices
    """

    def __init__(self, options, args, printouts=True):
        """ constructor

        :param options: command options
        :type options: :class:`optparse.Values`
        :param args: command arguments
        :type args: :obj:`list` <:obj:`str` >
        :param printouts: if printout is enable
        :type printouts: :obj:`bool`
        """
        Creator.__init__(self, options, args, printouts)
        #: (:obj:`dict` <:obj:`str`, :obj:`str` >) datasource xml dictionary
        self.datasources = {}
        #: (:obj:`dict` <:obj:`str`, :obj:`str` >) component xml dictionary
        self.components = {}
        #: component xml dictionary
        if options.xmlpackage:
            xmlPackageHandler.loadXMLTemplates(options.xmlpackage)
        else:
            xmlPackageHandler.loadXMLTemplates('nxstools.xmltemplates')
        #: (:obj:`str`) xml template component package path
        self.xmltemplatepath = xmlPackageHandler.packagepath
        #: (:obj:`str`) xml template component package
        self.xmlpackage = xmlPackageHandler.package

    def create(self):
        """ creates components of all online.xml complex devices
        """
        cpname = self.options.component
        if hasattr(self.options, "database") and \
           self.options.database:
            server = self.options.server
            if not self.options.overwrite:
                if self._areComponentsAvailable(
                        [cpname], server, self.options.lower):
                    raise CPExistsException(
                        "Component '%s' already exists." % cpname)
        elif not self.options.overwrite:
            existing = self._componentFilesExist(
                [cpname], self.options.file, self.options.directory)
            if existing:
                raise CPExistsException(
                    "Component files '%s' already exist." % existing)

        self.createXMLs()
        if not self.datasources and not self.components:
            raise CPExistsException(
                "Warning: Component %s cannot be created" % cpname)
        server = self.options.server
        if hasattr(self.options, "database") and \
           self.options.database:
            for dsname, dsxml in self.datasources.items():
                storeDataSource(dsname, dsxml, server)
            for cpname, cpxml in self.components.items():
                mand = False
                if hasattr(self.options, "mandatory") and \
                   self.options.mandatory:
                    mand = True
                storeComponent(cpname, cpxml, server, mand)
        else:
            for dsname, dsxml in self.datasources.items():
                with open("%s/%s%s.ds.xml" % (
                        self.options.directory,
                        self.options.file, dsname), "w") as myfile:
                    myfile.write(dsxml)
            for cpname, cpxml in self.components.items():
                with open("%s/%s%s.xml" % (
                        self.options.directory,
                        self.options.file, cpname), "w") as myfile:
                    myfile.write(cpxml)

    @classmethod
    def _replaceName(cls, filename, cpname, module=None):
        """ replaces name prefix of xml templates files

        :param filename: template filename
        :type filename: :obj:`str`
        :param cpname: output prefix
        :type cpname: :obj:`str`
        :param module: module name
        :type module: :obj:`str`
        :returns: output filename
        :rtype: :obj:`str`
        """
        if filename.endswith(".ds.xml"):
            filename = filename[:-7]
        elif filename.endswith(".xml"):
            filename = filename[:-4]
        sname = filename.split("_")
        if not module or module == sname[0]:
            sname[0] = cpname
        return "_".join(sname)

    def createXMLs(self):
        """ creates component xmls of all online.xml complex devices
        abstract method
        """
        pass


class CompareOnlineDS(object):

    """ comparing tool for online.xml files
    """

    def __init__(self, options, args, printouts=True):
        """ constructor

        :param options:  command options
        :type options: :class:`optparse.Values`
        :param args: command arguments
        :type args: :obj:`list` < :obj:`str` >
        :param printouts: if printout is enable
        :type printouts: :obj:`bool`
        """
        #: (:class:`optparse.Values`) creator options
        self.options = options
        #: (:obj:`list` < :obj:`str` >) creator arguments
        self.args = args
        #: (:obj:`bool`) if printout is enable
        self._printouts = printouts

    @classmethod
    def _getText(cls, node):
        """ provides xml content of the node

        :param node: DOM node
        :type node: :class:`lxml.etree.Element`
        :returns: xml content string
        :rtype: :obj:`str`
        """
        if node is None:
            return
        xml = _toxml(node)
        start = xml.find('>')
        end = xml.rfind('<')
        if start == -1 or end < start:
            return ""
        return xml[start + 1:end].replace("&lt;", "<").replace("&gt;", "<"). \
            replace("&quot;", "\"").replace("&amp;", "&")

    @classmethod
    def _getChildText(cls, parent, childname):
        """ provides text of child named by childname

        :param parent: parent node
        :type parent: :class:`lxml.etree.Element`
        :param childname: child name
        :type childname: :opj:`str`
        :returns: text string
        :rtype: :obj:`str`
        """

        children = parent.findall(childname)
        return cls._getText(children[0]) if len(children) else None

    def _load(self, fname):
        """ loads device data from online.xml file

        :param fname: filename
        :type fname: :obj:`str`
        :returns: dictionary with devices of the given name
        :rtype: :obj:`dict` <:obj:`str`, :obj:`list` <:class:`Device`>>
        """

        dct = {}
        hw = etree.parse(fname,
                         parser=XMLParser(collect_ids=False)).getroot()
        if hw.tag != 'hw':
            hw = hw.find('hw')
        for device in hw:
            if device.tag == 'device':
                name = self._getChildText(device, "name")
                if self.options.lower:
                    name = name.lower()
                dv = Device()
                dv.name = name
                dv.dtype = self._getChildText(device, "type")
                dv.module = self._getChildText(device, "module")
                dv.tdevice = self._getChildText(device, "device")
                dv.hostname = self._getChildText(device, "hostname")
                dv.sardananame = self._getChildText(device, "sardananame")
                dv.sardanahostname = self._getChildText(
                    device, "sardanahostname")
                sname = dv.sardananame or name
                if sname not in dct.keys():
                    dct[sname] = []
                dct[sname].append(dv)
        return dct

    def compare(self):
        if self._printouts:
            print("Comparing: %s\n" % " ".join(self.args))
        dct1 = self._load(self.args[0])
        dct2 = self._load(self.args[1])
        common = sorted(set(dct1.keys()) & set(dct2.keys()))
        d1md2 = sorted(set(dct1.keys()) - set(dct2.keys()))
        d2md1 = sorted(set(dct2.keys()) - set(dct1.keys()))
        addd1 = dict((str(k),
                      [(str(dv.name) if dv.name else dv.name)
                       for dv in dct1[k]])
                     for k in d1md2)
        addd2 = dict((str(k),
                      [(str(dv.name) if dv.name else dv.name)
                       for dv in dct2[k]])
                     for k in d2md1)
        diff = {}
        for name in common:
            ndiff = {}
            l1 = [True] * len(dct1[name])
            l2 = [True] * len(dct2[name])
            for i1, dv1 in enumerate(dct1[name]):
                for i2, dv2 in enumerate(dct2[name]):
                    if l1[i1] and l2[i2]:
                        res = dv1.compare(dv2)
                        if not res:
                            l1[i1] = False
                            l2[i2] = False
                            break
                        else:
                            ndiff["%s:%s" % (i1, i2)] = res
            if True in l1 and True not in l2:
                addd1[str(name)] = []
                for i1, dv in enumerate(dct1[name]):
                    if l1[i1]:
                        addd1[str(name)].append(
                            (str(dv.name) if dv.name else dv.name))
            elif True not in l1 and True in l2:
                addd2[str(name)] = []
                for i2, dv in enumerate(dct2[name]):
                    if l2[i2]:
                        addd2[str(name)].append(
                            (str(dv.name) if dv.name else dv.name))
            if True in l1 or True in l2:
                diff[str(name)] = []
                for i1, dv1 in enumerate(dct1[name]):
                    for i2, dv2 in enumerate(dct2[name]):
                        if l1[i1] and l2[i2]:
                            diff[str(name)].append(ndiff["%s:%s" % (i1, i2)])

        if self._printouts:
            import pprint
            print("Additional devices in '%s' {alias: [name]} :\n"
                  % self.args[0])
            pprint.pprint(addd1)
            print("\nAdditional devices in '%s' {alias: [name]} :\n"
                  % self.args[1])
            pprint.pprint(addd2)
            print("\nDiffrences in the common part:\n")
            pprint.pprint(diff)


class OnlineCPCreator(CPCreator):

    """ component creator of online components
    """

    def __init__(self, options, args, printouts=True):
        """ constructor

        :param options: command options
        :type options: :class:`optparse.Values`
        :param args: command arguments
        :type args: :obj:`list` < :obj:`str` >
        :param printouts: if printout is enable
        :type printouts: :obj:`bool`
        """
        CPCreator.__init__(self, options, args, printouts)

    def _printAction(self, dv, dscps=None):
        """ prints out information about the performed action

        :param dv: online device object
        :type dv: :class:`Device`
        :param dscps: datasource components
        :type dscps: :obj:`dict` <:obj:`str`, :obj:`list` < :obj:`str` > >
        """
        if self._printouts:
            if hasattr(self.options, "database") and \
               self.options.database:
                print("CREATING %s %s/%s %s" % (
                    str(dv.name) + ":" + " " * (34 - len(dv.name)),
                    dv.hostname,
                    str(dv.tdevice) + " " * (
                        60 - len(dv.tdevice) - len(dv.hostname)),
                    ",".join(dscps[dv.name])
                    if (dscps and dv.name in dscps and dscps[dv.name])
                    else ""))
            else:
                print("CREATING %s: %s/%s%s.ds.xml" % (
                    dv.tdevice, self.options.directory, self.options.file,
                    dv.name))

    def listcomponents(self):
        """ provides a list of components with xml templates

        :returns: list of components with xml templates
        :rtype: :obj:`list` <:obj:`str` >
        """
        hw = etree.parse(
            self.args[0],
            parser=XMLParser(collect_ids=False)).getroot()
        if hw.tag != 'hw':
            hw = hw.find('hw')
        cpnames = set()
        for device in hw:
            if device.tag == 'device':
                dvname = self._getChildText(device, "name")
                sardananame = self._getChildText(device, "sardananame")
                name = sardananame or dvname
                if self.options.lower:
                    name = name.lower()
                dv = Device()
                dv.name = name
                dv.dtype = self._getChildText(device, "type")
                dv.module = self._getChildText(device, "module")
                dv.tdevice = self._getChildText(device, "device")
                dv.hostname = self._getChildText(device, "hostname")
                dv.sardananame = self._getChildText(device, "sardananame")
                dv.sardanahostname = self._getChildText(
                    device, "sardanahostname")

                module = self._getModuleName(dv)
                if module:
                    if module.lower() in self.xmlpackage.moduleTemplateFiles:
                        cpnames.add(dv.name)
        return cpnames

    def listcomponenttypes(self):
        """ provides a list of standard component types

        :returns: list of standard component types
        :rtype: :obj:`list` <:obj:`str`>
        """
        return list(sorted(self.xmlpackage.moduleTemplateFiles.keys()))

    def createXMLs(self):
        """ creates component xmls of all online.xml complex devices
        """
        self.datasources = {}
        self.components = {}
        if self.options.component and self.options.cptype and \
           self.options.device:
            hw = [None]
        else:
            hw = etree.parse(
                self.args[0],
                parser=XMLParser(collect_ids=False)).getroot()
            if hw.tag != 'hw':
                hw = hw.find('hw')
        cpname = self.options.component
        tangohost = getServerTangoHost(
            self.options.external or self.options.server)
        for device in hw:
            if device is None or device.tag == 'device':
                if device is None:
                    name = cpname
                else:
                    dvname = self._getChildText(device, "name")
                    sardananame = self._getChildText(
                        device, "sardananame")
                    name = sardananame or dvname
                if self.options.lower:
                    name = name.lower()
                    cpname = cpname.lower()
                if name == cpname:
                    dv = Device()
                    dv.name = name
                    dv.dtype = self.options.cptype or \
                        self._getChildText(device, "type")
                    dv.module = self.options.cptype or \
                        self._getChildText(device, "module")
                    dv.tdevice = self.options.device or \
                        self._getChildText(device, "device")
                    hostname = None
                    if self.options.host:
                        host = self.options.host
                        port = self.options.port \
                            if self.options.port else "10000"
                        hostname = "%s:%s" % (host, port)
                    if hostname is None and device is None:
                        hostname = tangohost
                    if hostname is not None:
                        dv.hostname = hostname
                    if hostname is None and device is not None:
                        dv.hostname = self._getChildText(device, "hostname")
                    if device is not None:
                        dv.sardananame = \
                            self._getChildText(device, "sardananame")
                        dv.sardanahostname = self._getChildText(
                            device, "sardanahostname")

                    dv.findDevice(tangohost)
                    try:
                        dv.splitHostPort()
                    except Exception:
                        if self._printouts:
                            print("ERROR %s: host for module %s of %s "
                                  "type not defined"
                                  % (dv.name, dv.module, dv.dtype))
                        continue
                    if self.options.cptype:
                        module = self.options.cptype
                    else:
                        module = self._getModuleName(dv)
                    if module:
                        if module.lower() in \
                           self.xmlpackage.moduleMultiAttributes.keys():
                            multattr = self.xmlpackage.moduleMultiAttributes[
                                module.lower()]
                            for at in multattr:
                                dsname = "%s_%s" % (
                                    dv.name, at.lower())
                                xml = self._createTangoDataSource(
                                    dsname, None, None, None,
                                    dv.tdevice, at, dv.host, dv.port,
                                    "%s_" % (dv.name.lower()))
                                self.datasources[dsname] = xml
                                mdv = copy.copy(dv)
                                mdv.name = dsname
                                mdv.attribute = at
                                self._printAction(mdv)
                        smodule = "%s@pool" % module.lower()
                        if smodule in \
                           self.xmlpackage.moduleMultiAttributes.keys():
                            smultattr = self.xmlpackage.moduleMultiAttributes[
                                smodule]
                            if smultattr and not dv.sdevice:
                                raise Exception(
                                    "Device %s cannot be found" % dv.name)
                            for at in smultattr:
                                dsname = "%s_%s" % (
                                    dv.name,
                                    at.lower())
                                xml = self._createTangoDataSource(
                                    dsname, None, None, None,
                                    dv.sdevice, at, dv.shost, dv.sport,
                                    "%s_" % (dv.name))
                                #   "__CLIENT__")
                                self.datasources[dsname] = xml
                                mdv = copy.copy(dv)
                                mdv.name = dsname
                                mdv.tdevice = dv.sdevice
                                mdv.hostname = "%s:%s" % (dv.shost, dv.sport)
                                mdv.attribute = at
                                self._printAction(mdv)
                        if module.lower() \
                           in self.xmlpackage.moduleTemplateFiles:
                            xmlfiles = self.xmlpackage.moduleTemplateFiles[
                                module.lower()]
                            for xmlfile in xmlfiles:
                                newname = self._replaceName(xmlfile, cpname)
                                with open(
                                        '%s/%s' % (
                                            self.xmltemplatepath, xmlfile), "r"
                                ) as content_file:
                                    xmlcontent = content_file.read()
                                xml = xmlcontent.replace("$(name)", cpname)\
                                    .replace("$(device)", dv.tdevice)\
                                    .replace("$(__entryname__)",
                                             (self.options.entryname
                                              or "scan"))\
                                    .replace("$(__insname__)",
                                             (self.options.insname
                                              or "instrument"))\
                                    .replace("$(hostname)", dv.hostname)
                                mdv = copy.copy(dv)
                                mdv.name = newname
                                self._printAction(mdv)
                                if xmlfile.endswith(".ds.xml"):
                                    self.datasources[newname] = xml
                                else:
                                    self.components[newname] = xml


class SECoPCPCreator(CPCreator):

    """ component creator of secop components
    """

    def __init__(self, options, args, printouts=True):
        """ constructor

        :param options: command options
        :type options: :class:`optparse.Values`
        :param args: command arguments
        :type args: :obj:`list` < :obj:`str` >
        :param printouts: if printout is enable
        :type printouts: :obj:`bool`
        """
        CPCreator.__init__(self, options, args, printouts)

    def _printAction(self, name, ds=False):
        """ prints out information about the performed action

        :param name: component name
        :type name: :obj:`str`
        """
        if self._printouts:
            if hasattr(self.options, "database") and \
               self.options.database:
                print("CREATING '%s' of secop on '%s'" % (
                    name,
                    self.options.server))
            else:
                ext = ".ds" if ds else ""
                print("CREATING '%s' of secop in '%s/%s%s%s.xml'" % (
                    name,
                    self.options.directory,
                    self.options.file,
                    name, ext))

    def listmodules(self):
        """ provides a list of modules for the secop node

        :returns: list of modules for the secop node
        :rtype: :obj:`list` <:obj:`str` >
        """
        names = []
        conf = {}
        if self.options.json:
            with open(self.options.json) as fl:
                conf = json.load(fl)
        else:
            conf = secop_cmd(
                "describe", self.options.host, int(self.options.port)) or {}
        modules = conf.get("modules", {})
        if modules:
            names = [mname for mname in modules.keys()]
        # print(json.dumps(conf))
        return names

    def __createSECoPTree(self, df, name, conf, samplename=None,
                          sampleenvname=None,
                          modulenames=None, canfail=None,
                          environments=None,
                          meanings=None, first=None, transattrs=None,
                          dynamiclinks=False, samplenxdata=False):
        """ create nexus node tree

        :param df: definition parent node
        :type df: :class:'nxstools.nxsxml.XMLFile'
        :param name: node name
        :type name: :obj:`str`
        :param conf: secop configuration
        :type conf: :obj:`dict`
        :param samplename: sample name
        :type samplename: :obj:`str`
        :param sampleenvname: sample environment name
        :type sampleenvname: :obj:`str`
        :param modulenames: module names
        :typae modulenames: :obj:`list` <:obj:`str`>
        :param canfail: can fail strategy flag
        :type canfail: :obj:`bool`
        :param environments: environments to link separated by comman
        :type environments: :obj:`str`
        :param meanings: physical quantity meaning to link separated by comman
        :type meanings: :obj:`str`
        :param first: first targets to link separated by comman
        :type first: :obj:`str`
        :param transattrs: JSON dictionary with transformation attributes
        :type transattrs: :obj:`str`
        :param dynamiclinks: dynamic links flag
        :type dynamiclinks: :obj:`bool`
        :param samplenxdata: sample nxdata
        :type samplenxdata: :obj:`bool`
        """
        ename = "$var.entryname#'$(__entryname__)'$var.serialno".replace(
                    "$(__entryname__)", (self.options.entryname or "scan"))
        entry = NGroup(df, ename, "NXentry")
        samplename = samplename or "sample"
        sampleenvname = sampleenvname or "sample_environment"
        sample = NGroup(entry, samplename, "NXsample")
        field = NField(sample, 'type', 'NX_CHAR')
        field.setText("sample")
        field.setStrategy('INIT')

        sampleenv = NGroup(entry, sampleenvname, "NXsample")
        field = NField(sampleenv, 'type', 'NX_CHAR')
        field.setText("sample environment")
        field.setStrategy('INIT')

        modules = conf.get("modules", {})
        senv = None
        seenv = None

        for mname, mconf in modules.items():
            if mname and (not senv or not seenv):
                if not modulenames or mname in modulenames:
                    if "meaning" in mconf.keys() and \
                       isinstance(mconf["meaning"], dict):
                        if "belongs_to" in mconf["meaning"].keys() and \
                                mconf["meaning"]["belongs_to"] == "sample":
                            if not senv:
                                senv = NGroup(sample, name or "environment",
                                              "NXenvironment")
                        else:
                            if not seenv:
                                seenv = NGroup(sampleenv,
                                               name or "environment",
                                               "NXenvironment")
                    else:
                        if not senv and "meaning" in mconf.keys():
                            senv = NGroup(sample, name or "environment",
                                          "NXenvironment")
                        if not seenv and "meaning" not in mconf.keys():
                            seenv = NGroup(sampleenv, name or "environment",
                                           "NXenvironment")
        envs = [senv, seenv]
        for env in envs:
            if env:
                if 'equipment_id' in conf.keys():
                    field = NField(env, 'name', 'NX_CHAR')
                    field.setText("%s" % str(conf['equipment_id']))
                    field.setStrategy('INIT')
                if name or 'equipment_id' in conf.keys():
                    field = NField(env, 'short_name', 'NX_CHAR')
                    if name:
                        field.setText("%s" % str(name))
                    elif 'equipment_id' in conf.keys():
                        field.setText("%s" % str(conf['equipment_id']))
                    field.setStrategy('INIT')
                if 'firmware' in conf.keys() or 'version' in conf.keys():
                    field = NField(env, 'type', 'NX_CHAR')
                    txt = ""
                    if 'firmware' in conf.keys():
                        txt = str(conf['firmware'])
                    if 'version' in conf.keys():
                        if txt:
                            txt = "%s (%s)" % (txt, str(conf['version']))
                        else:
                            txt = "(%s)" % (str(conf['version']))
                    field.setText(txt)
                    field.setStrategy('INIT')
                if 'description' in conf.keys():
                    field = NField(env, 'description', 'NX_CHAR')
                    field.setText("%s" % str(conf['description']))
                    field.setStrategy('INIT')

        targets = (first or "").split(",")
        lmeanings = (meanings or "").split(",")
        lenvironments = (environments or "").split(",")
        try:
            trattrs = json.loads(transattrs or "{}")
        except Exception:
            trattrs = {}
        links = {}
        for mname, mconf in modules.items():
            if mname:
                if not modulenames or mname in modulenames:
                    lk = self.__createSECoPSensor(
                        senv, seenv, mname, mconf, name, canfail, samplename,
                        sampleenvname, trattrs)
                    if lk and isinstance(lk, dict):
                        links.update(lk)
        ename = \
            "$var.entryname#'$(__entryname__)'" \
            "$var.serialno".replace(
                "$(__entryname__)",
                (self.options.entryname or "scan"))
        created = []
        created_trans = []
        trans = None
        for tg in targets:
            try:
                stg = "/".join(tg.split("/")[-3:])
            except Exception:
                stg = None
            if tg in links.keys() or stg and stg in links.keys():
                mn = links[tg][0]
                NLink(sample, mn, tg)
                created.append(mn)
        llinks = sorted([(tg, mns[0], mns[1]) for tg, mns in links.items()],
                        key=itemgetter(2), reverse=True)
        if dynamiclinks or samplenxdata:
            self.createSECoPLinkDS(
                ename, samplename, sampleenvname,
                meanings or "", environments or "")
        if dynamiclinks:
            ae = sample.addAttr(
                'secop_env_links', "NX_CHAR",
                "$datasources.sample_env_links")
            ae.setStrategy("FINAL")
            al = sample.addAttr(
                'secop_log_links', "NX_CHAR",
                "$datasources.sample_log_links")
            al.setStrategy("FINAL")
        if samplenxdata:
            al = sample.addAttr(
                'sample_nxdata', "NX_CHAR",
                "$datasources.sample_nxdata")
            al.setStrategy("FINAL")
            al = sampleenv.addAttr(
                'sampleenv_nxdata', "NX_CHAR",
                "$datasources.sampleenv_nxdata")
            al.setStrategy("FINAL")

        for target, mn, semn in llinks:
            starget = target.split("/")
            if not dynamiclinks:
                if mn in lenvironments and "%s_env" % mn not in created:
                    env = NGroup(
                        sample, "%s_env" % mn, "NXenvironment")

                    NLink(env, starget[-2], "/".join(starget[:-1]))
                    NLink(env, "description",
                          "/".join(starget[:-2]) + "/description")
                    NLink(env, "name",
                          "/".join(starget[:-2]) + "/name")
                    NLink(env, "short_name",
                          "/".join(starget[:-2]) + "/short_name")
                    NLink(env, "type", "/".join(starget[:-2]) + "/type")
                    created.append("%s_env" % mn)
                if mn in lmeanings and mn not in created:
                    NLink(sample, mn, target)
                    created.append(mn)

            if mn in trattrs.keys():
                nm = "%s_%s" % (starget[-3], starget[-2])
                if nm not in created_trans:
                    if trans is None:
                        trans = NGroup(
                            sample, "transformations", "NXtransformations")
                    NLink(trans, nm, target + "/value")
                    created_trans.append(nm)

    def __createSECoPSensor(self, senv, seenv, name, conf, nodename,
                            canfail=None, samplename="sample",
                            sampleenvname="sample_environment",
                            trattrs=None):
        """ create nexus node tree

        :param senv: definition parent node
        :type senv: :class:'nxstools.nxsxml.XMLFile'
        :param seenv: definition parent node
        :type seenv: :class:'nxstools.nxsxml.XMLFile'
        :param name: sensor name
        :type name: :obj:`str`
        :param conf: secop configuration
        :type conf: :obj:`dict`
        :param nodename: node name
        :type nodename: :obj:`str`
        :param canfail: can fail strategy flag
        :type canfail: :obj:`bool`
        :param samplename: sample group name i.e. sample
        :type samplename: :obj:`str`
        :param sampleenvname: sample environment group name
        :type sampleenvname: :obj:`str`
        :param trattrs: dictionary with transformation attributes
        :type trattrs: :obj:`dict` <:obj:`str`,:obj:`dict` <:obj:`str`,`and`>>
        :returns: links targets and meaning names
        :rtype: :obj:`dict`< :obj:`str`, (:obj:`str`, :obj:`str`) >
        """
        if 'meaning' in conf.keys():
            meaning = conf['meaning']
            if isinstance(meaning, dict):
                mdict = meaning
                env = seenv
                meaning = None
                basename = sampleenvname

                if "belongs_to" in mdict.keys() and \
                        mdict["belongs_to"] == "sample":
                    env = senv
                    basename = samplename
                if "function" in mdict.keys():
                    meaning = mdict["function"]
            else:
                env = senv
                basename = samplename
        else:
            meaning = None
            env = seenv
            basename = sampleenvname

        links = {}
        trattrs = trattrs or {}
        mgr = NGroup(env, name, "NXsensor")
        if 'description' in conf.keys():
            field = NField(mgr, 'name', 'NX_CHAR')
            field.setText("%s" % str(name))
            field.setStrategy('INIT')
        afunction = None
        alink = None
        akey = None
        if 'meaning' in conf.keys():
            meaning = conf['meaning']
            importance = None
            if isinstance(meaning, list):
                if len(meaning) > 1:
                    try:
                        importance = int(meaning[1])
                    except Exception:
                        importance = None
                if len(meaning) > 0:
                    meaning = meaning[0]
                    afunction = meaning
            elif isinstance(meaning, dict):
                try:
                    alink = meaning["link"]
                except Exception:
                    alink = None
                try:
                    akey = meaning["key"]
                except Exception:
                    akey = None
                try:
                    importance = int(meaning["importance"])
                except Exception:
                    importance = None
                try:
                    meaning = meaning["function"]
                    afunction = meaning
                except Exception:
                    meaning = None
            else:
                afunction = meaning
            field = NField(mgr, 'measurement', 'NX_CHAR')
            field.setStrategy('INIT')
            meaning = mnTme[meaning] if meaning in mnTme.keys() else ""
            field.setText(meaning)
            if importance is not None:
                mimp = NAttr(field, "secop_importance", "NX_INT32")
                mimp.setText(str(importance))
            if akey is not None:
                mimp = NAttr(field, "secop_key", "NX_CHAR")
                mimp.setText(str(akey))
            if alink is not None:
                mimp = NAttr(field, "secop_link", "NX_CHAR")
                mimp.setText(str(alink))
            if afunction is not None:
                mimp = NAttr(field, "secop_function", "NX_CHAR")
                mimp.setText(str(afunction))
        if 'implementation' in conf.keys():
            field = NField(mgr, 'model', 'NX_CHAR')
            field.setText("%s" % str(conf['implementation']))
            field.setStrategy('INIT')
        if 'description' in conf.keys():
            field = NField(mgr, 'description', 'NX_CHAR')
            field.setText("%s" % str(conf['description']))
            field.setStrategy('INIT')
        params = conf.get("accessibles", {})
        if params:
            par = NGroup(mgr, "parameters", "NXcollection")
            for pname, pconf in params.items():
                if pname:
                    if pname == "value":
                        di = pconf.get("datainfo")
                        if di:
                            dtype = di.get("type")
                            nxtype = npTn.get(dtype, "NX_CHAR")
                            units = di.get("unit")
                            minval = di.get("min")
                            maxval = di.get("max")
                        log = NGroup(mgr, "value_log", "NXlog")
                        field = NField(log, 'value', nxtype)
                        if meaning:
                            ename = \
                                "$var.entryname#'$(__entryname__)'" \
                                "$var.serialno".replace(
                                    "$(__entryname__)",
                                    (self.options.entryname or "scan"))
                            target = "/%s/%s/%s/%s/value_log" % \
                                (ename, basename, nodename, name)
                            links[target] = (meaning, afunction)
                        dsname = "%s_%s" % (nodename, name)
                        timedsname = "%s_%s_time" % (nodename, name)
                        if self.options.lower:
                            dsname = dsname.lower()
                            timedsname = timedsname.lower()
                        self.createSECoPDS(dsname,
                                           "read %s:%s" % (name, pname),
                                           dsname, "[0]")
                        field.setText("$datasources.%s" % dsname)
                        if units:
                            field.setUnits(units)
                        if afunction and afunction in trattrs.keys():
                            try:
                                attrs = dict(trattrs[afunction])
                            except Exception:
                                attrs = {}
                            for nm, vl in attrs.items():
                                if isinstance(vl, list):
                                    if vl and isinstance(vl[0], str):
                                        vct = NAttr(field, nm, "NX_CHAR")
                                        vct.setText("\n ".join(vl))
                                    else:
                                        vct = NAttr(field, nm, "NX_FLOAT64")
                                        vct.setText(
                                            " ".join([str(st) for st in vl]))
                                    d = NDimensions(vct, "1")
                                    d.dim("1", str(len(vl)))
                                    vct.setStrategy("INIT")
                                else:
                                    field.addTagAttr(nm, vl)
                            ename = \
                                "$var.entryname#'$(__entryname__)'" \
                                "$var.serialno".replace(
                                    "$(__entryname__)",
                                    (self.options.entryname or "scan"))
                            target = "/%s/%s/%s/%s/value_log" % \
                                (ename, basename, nodename, name)
                            links[target] = (afunction, afunction)
                        strategy = self.options.strategy
                        field.setStrategy(strategy)
                        field = NField(log, 'time', "NX_FLOAT64")
                        field.setText(
                            "$datasources.%s" % timedsname)
                        at = field.addAttr(
                            'start', "NX_DATE_TIME",
                            "$datasources.client_start_time")
                        at.setStrategy("INIT")
                        field.setUnits("s")
                        field.setStrategy(strategy)
                        if minval:
                            field = NField(log, 'manimum_value', nxtype)
                            field.setStrategy('INIT')
                            field.setText(str(minval))
                            if units:
                                field.setUnits(units)
                        if maxval:
                            field = NField(log, 'maximum_value', nxtype)
                            field.setStrategy('INIT')
                            field.setText(str(maxval))
                            if units:
                                field.setUnits(units)
                    elif pname == "status":
                        self.__createSECoPParam(
                            par, pname, pconf, nodename, name, canfail,
                            "[0,0]", "int")
                    else:
                        self.__createSECoPParam(
                            par, pname, pconf, nodename, name, canfail)
                        if pname == "target":
                            ename = \
                                "$var.entryname#'$(__entryname__)'" \
                                "$var.serialno".replace(
                                    "$(__entryname__)",
                                    (self.options.entryname or "scan"))
                            NLink(mgr, "value",
                                  "/%s/%s/%s/%s/parameters/target/value" %
                                  (ename, basename, nodename, name))
        return links

    def __createSECoPParam(self, par, name, conf, nodename, modname,
                           canfail=None, access=None, accesstype=None):
        """ create nexus node tree

        :param env: definition parent node
        :type env: :class:'nxstools.nxsxml.XMLFile'
        :param name: parameter name
        :type name: :obj:`str`
        :param conf: secop configuration
        :type conf: :obj:`dict`
        :param nodename: node name
        :type nodename: :obj:`str`
        :param modname: sensor name
        :type modname: :obj:`str`
        :param canfail: can fail strategy flag
        :type canfail: :obj:`bool`
        """
        di = conf.get("datainfo")
        if di:
            dtype = di.get("type")
            if dtype == "command":
                return
            if dtype not in npTn.keys() and not access:
                return
            nxtype = npTn.get(dtype, "NX_CHAR")
            if accesstype in npTn.keys():
                nxtype = npTn.get(accesstype)
            units = di.get("unit")
            minval = di.get("min")
            maxval = di.get("max")
        access = access or "[0]"
        log = NGroup(par, name, "NXlog")
        field = NField(log, "value", nxtype)
        dsname = "%s_%s_%s" % (nodename, modname, name)
        timedsname = "%s_%s_%s_time" % (nodename, modname, name)
        if self.options.lower:
            dsname = dsname.lower()
            timedsname = timedsname.lower()
        field.setText("$datasources.%s" % (dsname))
        pstrategy = self.options.paramstrategy
        self.createSECoPDS(dsname,
                           "read %s:%s" % (modname, name),
                           dsname, access)
        field.setStrategy(pstrategy)
        if units:
            field.setUnits(units)
        field = NField(log, 'time', "NX_FLOAT64")
        field.setText(
            "$datasources.%s" % timedsname)
        at = field.addAttr(
            'start', "NX_DATE_TIME", "$datasources.client_start_time")
        at.setStrategy("INIT")
        field.setUnits("s")
        field.setStrategy(pstrategy)
        if minval:
            field = NField(log, 'manimum_value', nxtype)
            field.setStrategy('INIT')
            field.setText(str(minval))
            if units:
                field.setUnits(units)
        if maxval:
            field = NField(log, 'maximum_value', nxtype)
            field.setStrategy('INIT')
            field.setText(str(maxval))
            if units:
                field.setUnits(units)

    def createXMLs(self):
        """ creates component xmls of all online.xml complex devices
        """
        self.datasources = {}
        self.components = {}
        cpnames = self.args
        conf = {}
        if self.options.json:
            with open(self.options.json) as fl:
                conf = json.load(fl)
        else:
            conf = secop_cmd(
                "describe", self.options.host, int(self.options.port))
        if isinstance(conf, dict):
            # dump = \
            #     json.dumps(conf, sort_keys=True, indent=4)
            # print("%s" % dump)
            cpname = self.options.component
            if 'description' in conf.keys() and not cpname:
                eid = str(conf['equipment_id']).split(".")
                if eid and eid[0]:
                    cpname = eid[0]
                else:
                    des = str(conf['description']).split("\n")
                    if des and des[0]:
                        cpname = des[0]
                cpname = cpname.replace("[", "").\
                    replace("]", "_").replace(",", "_")
                if not cpname:
                    cpname = "secop"
            fname = "%s%s.xml" % (self.options.file, cpname)
            if self.options.lower:
                fname = fname.lower()
                cpname = cpname.lower()
            df = XMLFile("%s/%s" % (self.options.directory, fname))
            self.__createSECoPTree(df, cpname, conf, self.options.samplename,
                                   self.options.sampleenvname,
                                   cpnames, self.options.canfail,
                                   self.options.environments,
                                   self.options.meanings,
                                   self.options.first,
                                   self.options.transattrs,
                                   self.options.dynamiclinks,
                                   self.options.samplenxdata)
            self._printAction(cpname)
            self.components[cpname] = df.prettyPrint()

    def createSECoPDS(self, dsname, message, group=None, access=None,
                      host=None, port=None, timeout=None):
        """ create SECoP datasource

        :param dsname: datasource name
        :type dsname: :obj:`str`
        :param message: secop command
        :type message: :obj:`str`
        :param group: secop group name
        :type group: :obj:`str`
        :param access: secop attribute access list
        :type access: :obj:`str`
        :param host: secop host name
        :type host: :obj:`str`
        :param port: secop port name
        :type port: :obj:`str` or :obj:`int`
        :param port: minimum timeout
        :type port: :obj:`str` or :obj:`float`
        """
        if access is not None and group is not None:
            module = 'groupsecop'
        elif group is not None:
            module = 'secop'
        else:
            module = 'singlesecop'

        if module in self.xmlpackage.standardComponentTemplateFiles:
            xmlfiles = self.xmlpackage.standardComponentTemplateFiles[module]
        else:
            if os.path.isfile("%s/%s.xml" % (self.xmltemplatepath, module)):
                xmlfiles = ["%s.xml" % module]
        params = {}

        host = self.options.host if host is None else host
        port = self.options.port if port is None else port
        timeout = str(self.options.timeout) \
            if timeout is None else str(timeout)
        if host is not None:
            params["host"] = host
        if port is not None:
            params["port"] = str(port)
        if message:
            params["message"] = message
        if timeout:
            params["timeout"] = timeout
        if access:
            params["access"] = access
        if group:
            params["group"] = group
        if self.options.lower:
            dsname = dsname.lower()

        for xmlfile in xmlfiles:
            # print(xmlfile)
            newname = self._replaceName(xmlfile, dsname, module)
            with open(
                    '%s/%s' % (
                        self.xmltemplatepath, xmlfile), "r"
            ) as content_file:
                xmlcontent = content_file.read()
                xml = xmlcontent.replace("$(name)", dsname)
                missing = []
                for var, desc in self.xmlpackage.standardComponentVariables[
                        module].items():
                    if var in params.keys():
                        xml = xml.replace("$(%s)" % var, params[var])
                    elif desc["default"] is not None:
                        xml = xml.replace("$(%s)" % var, desc["default"])
                    else:
                        missing.append(var)
                if missing:
                    if sys.version_info > (3,):
                        root = et.fromstring(
                            bytes(xml, "UTF-8"),
                            parser=XMLParser(collect_ids=False))
                    else:
                        root = et.fromstring(
                            xml,
                            parser=XMLParser(collect_ids=False))
                    nodes = root.findall(".//attribute")
                    nodes.extend(root.findall(".//field"))
                    nodes.extend(root.findall(".//link"))
                    grnodes = root.findall(".//group")
                    for node in nodes:
                        text = self.__getText(node)
                        for ms in missing:
                            label = "$(%s)" % ms
                            if label in text:
                                parent = node.getparent()
                                parent.remove(node)
                                break
                    for node in grnodes:
                        text = node.attrib["name"]
                        if text and "$(" in text:
                            for ms in missing:
                                label = "$(%s)" % ms
                                if label in text:
                                    parent = node.getparent()
                                    parent.remove(node)
                                    break
                    xml = _simpletoxml(root)
                    if self._printouts:
                        print("MISSING %s" % missing)
                    errors = []
                    for var in missing:
                        if "s.$(%s)" % var in xml:
                            errors.append(var)
                    if errors:
                        print(
                            "WARNING: %s cannot be created without %s"
                            % (var, errors))
                        continue

                    for var in missing:
                        xml = xml.replace("$(%s)" % var, "")
                    lines = xml.split('\n')
                    xml = '\n'.join([x for x in lines if len(x.strip())])
                if xmlfile.endswith(".ds.xml"):
                    self._printAction(newname, True)
                    self.datasources[newname] = xml
                else:
                    self._printAction(newname)
                    self.components[newname] = xml

    def createSECoPLinkDS(self, entryname, samplename, sampleenvname,
                          meanings, environments):
        """ create SECoP datasource

        :param entryname: secop entry name
        :type entryname: :obj:`str`
        :param samplename: secop sample name
        :type samplename: :obj:`str`
        :param sampleenvname: secop sample name
        :type sampleenvname: :obj:`str`
        :param meanings: secop meanings list
        :type meanings: :obj:`str`
        :param environments: secop environments list
        :type environments: :obj:`str`
        """
        module = 'secoplinks'
        dsname = "secop"

        if module in self.xmlpackage.standardComponentTemplateFiles:
            xmlfiles = self.xmlpackage.standardComponentTemplateFiles[module]
        else:
            if os.path.isfile("%s/%s.xml" % (self.xmltemplatepath, module)):
                xmlfiles = ["%s.xml" % module]
        params = {}

        params["entryname"] = entryname
        params["samplename"] = samplename
        params["sampleenvname"] = sampleenvname
        params["meanings"] = meanings
        params["environments"] = environments
        if self.options.lower:
            dsname = dsname.lower()

        for xmlfile in xmlfiles:
            # print(xmlfile)
            newname = self._replaceName(xmlfile, dsname, module)
            with open(
                    '%s/%s' % (
                        self.xmltemplatepath, xmlfile), "r"
            ) as content_file:
                xmlcontent = content_file.read()
                xml = xmlcontent.replace("$(name)", dsname).replace(
                    "$(__entryname__)",
                    (self.options.entryname or "scan")).replace(
                        "$(__insname__)",
                        (self.options.insname
                         or "instrument"))
                missing = []
                for var, desc in self.xmlpackage.standardComponentVariables[
                        module].items():
                    if var in params.keys():
                        xml = xml.replace("$(%s)" % var, params[var])
                    elif desc["default"] is not None:
                        xml = xml.replace("$(%s)" % var, desc["default"])
                    else:
                        missing.append(var)
                if missing:
                    if sys.version_info > (3,):
                        root = et.fromstring(
                            bytes(xml, "UTF-8"),
                            parser=XMLParser(collect_ids=False))
                    else:
                        root = et.fromstring(
                            xml,
                            parser=XMLParser(collect_ids=False))
                    nodes = root.findall(".//attribute")
                    nodes.extend(root.findall(".//field"))
                    nodes.extend(root.findall(".//link"))
                    grnodes = root.findall(".//group")
                    for node in nodes:
                        text = self.__getText(node)
                        for ms in missing:
                            label = "$(%s)" % ms
                            if label in text:
                                parent = node.getparent()
                                parent.remove(node)
                                break
                    for node in grnodes:
                        text = node.attrib["name"]
                        if text and "$(" in text:
                            for ms in missing:
                                label = "$(%s)" % ms
                                if label in text:
                                    parent = node.getparent()
                                    parent.remove(node)
                                    break
                    xml = _simpletoxml(root)
                    if self._printouts:
                        print("MISSING %s" % missing)
                    errors = []
                    for var in missing:
                        if "s.$(%s)" % var in xml:
                            errors.append(var)
                    if errors:
                        print(
                            "WARNING: %s cannot be created without %s"
                            % (var, errors))
                        continue

                    for var in missing:
                        xml = xml.replace("$(%s)" % var, "")
                    lines = xml.split('\n')
                    xml = '\n'.join([x for x in lines if len(x.strip())])
                if xmlfile.endswith(".ds.xml"):
                    self._printAction(newname, True)
                    self.datasources[newname] = xml
                else:
                    self._printAction(newname)
                    self.components[newname] = xml

    def create(self):
        """ creates components of all online.xml complex devices
        """
        cpnames = self.args
        for cpname in cpnames:
            if hasattr(self.options, "database") and \
               self.options.database:
                server = self.options.server
                if not self.options.overwrite:
                    if self._areComponentsAvailable(
                            [cpname], server, self.options.lower):
                        raise CPExistsException(
                            "Component '%s' already exists." % cpname)
            elif not self.options.overwrite:
                existing = self._componentFilesExist(
                    [cpname], self.options.file, self.options.directory)
                if existing:
                    raise CPExistsException(
                        "Component files '%s' already exist." % existing)

        self.createXMLs()
        if not self.datasources and not self.components:
            raise CPExistsException(
                "Warning: Components %s cannot be created" % cpnames)
        server = self.options.server
        if hasattr(self.options, "database") and \
           self.options.database:
            for dsname, dsxml in self.datasources.items():
                storeDataSource(dsname, dsxml, server)
            for cpname, cpxml in self.components.items():
                mand = False
                if hasattr(self.options, "mandatory") and \
                   self.options.mandatory:
                    mand = True
                storeComponent(cpname, cpxml, server, mand)
        else:
            for dsname, dsxml in self.datasources.items():
                with open("%s/%s%s.ds.xml" % (
                        self.options.directory,
                        self.options.file, dsname), "w") as myfile:
                    myfile.write(dsxml)
            for cpname, cpxml in self.components.items():
                # print(cpname)
                with open("%s/%s%s.xml" % (
                        self.options.directory,
                        self.options.file, cpname), "w") as myfile:
                    # print("%s/%s%s.xml" % (
                    #     self.options.directory,
                    #     self.options.file, cpname))
                    myfile.write(cpxml)

    @classmethod
    def _replaceName(cls, filename, cpname, module=None):
        """ replaces name prefix of xml templates files

        :param filename: template filename
        :type filename: :obj:`str`
        :param cpname: output prefix
        :type cpname: :obj:`str`
        :param module: module name
        :type module: :obj:`str`
        :returns: output filename
        :rtype: :obj:`str`
        """
        if filename.endswith(".ds.xml"):
            filename = filename[:-7]
        elif filename.endswith(".xml"):
            filename = filename[:-4]
        sname = filename.split("_")
        if not module or module == sname[0]:
            sname[0] = cpname
        return "_".join(sname)


class StandardCPCreator(CPCreator):

    """ component creator of standard templates
    """

    def __init__(self, options, args, printouts=True):
        """ constructor

        :param options: command options
        :type options: :class:`optparse.Values`
        :param args: command arguments
        :type args: :obj:`list` < :obj:`str` >
        :param printouts: if printout is enable
        :type printouts: :obj:`bool`
        """
        CPCreator.__init__(self, options, args, printouts)
        self.__params = {}
        self.__specialparams = {}

    def listcomponenttypes(self):
        """ provides a list of standard component types

        :returns: list of standard component types
        :rtype: :obj:`list` <:obj:`str`>
        """
        return list(sorted(self.xmlpackage.standardComponentVariables.keys()))

    def listcomponentvariables(self):
        """ provides a list of standard component types

        :returns: list of standard component types
        :rtype: :obj:`list` <:obj:`str`>
        """

        if self.options.cptype not \
           in self.xmlpackage.standardComponentVariables.keys():
            raise Exception(
                "Component type %s not in %s" %
                (self.options.cptype,
                 list(self.xmlpackage.standardComponentVariables.keys())))
        return self.xmlpackage.standardComponentVariables[
            self.options.cptype]

    def __setspecialparams(self):
        """ sets special parameters,
        i.e. __tangohost__, __tangoport__ and __configdevice__

        """
        server = self.options.external or self.options.server
        host, port = getServerTangoHost(server).split(":")
        self.__specialparams['__tangohost__'] = host
        self.__specialparams['__tangoport__'] = port
        if server:
            proxy = openServer(server)
            self.__specialparams['__configdevice__'] = proxy.name()
        else:
            self.__specialparams['__configdevice__'] = None

    @classmethod
    def _getChildText(cls, parent, childname):
        """ provides text of child named by childname

        :param parent: parent node
        :type parent: :class:`lxml.etree.Element`
        :param childname: child name
        :type childname: :opj:`str`
        :returns: text string
        :rtype: :obj:`str`
        """

        children = parent.findall(childname)
        return cls._getText(children[0]) if len(children) else None

    def createXMLs(self):
        """ creates component xmls of all online.xml complex devices
        """
        self.datasources = {}
        self.components = {}
        self.__setspecialparams()
        if self.args:
            self.__params = dict(zip(self.args[::2], self.args[1::2]))
        else:
            self.__params = {}
        cpname = self.options.component
        module = self.options.cptype
        if self.options.lower:
            cpname = cpname.lower()
            module = module.lower()
        if module not in self.xmlpackage.standardComponentVariables.keys():
            raise Exception(
                "Component type %s not in %s" %
                (module,
                 list(self.xmlpackage.standardComponentVariables.keys()))
            )

        xmlfiles = []
        if module in self.xmlpackage.standardComponentTemplateFiles:
            xmlfiles = self.xmlpackage.standardComponentTemplateFiles[module]
        else:
            if os.path.isfile("%s/%s.xml" % (self.xmltemplatepath, module)):
                xmlfiles = ["%s.xml" % module]

        hw = []
        if self.options.onlinexmlfile:
            hw = etree.parse(
                self.options.onlinexmlfile,
                parser=XMLParser(collect_ids=False)).getroot()
            if hw.tag != 'hw':
                hw = hw.find('hw')
        dv = None
        for device in hw:
            if device is None or device.tag == 'device':
                dvname = self._getChildText(device, "name")
                sardananame = self._getChildText(
                    device, "sardananame")
                name = sardananame or dvname
                if self.options.lower:
                    name = name.lower()
                if name == cpname:
                    tdevice = self._getChildText(device, "device")
                    hostname = self._getChildText(device, "hostname")
        for xmlfile in xmlfiles:
            # print(xmlfile)
            newname = self._replaceName(xmlfile, cpname, module)
            with open(
                    '%s/%s' % (
                        self.xmltemplatepath, xmlfile), "r"
            ) as content_file:
                xmlcontent = content_file.read()
                xml = xmlcontent.replace("$(name)", cpname).replace(
                    "$(__entryname__)",
                    (self.options.entryname or "scan")).replace(
                        "$(__insname__)",
                        (self.options.insname
                         or "instrument"))
                if dv:
                    if dv is not None:
                        xmlcontent = xmlcontent.replace(
                            "$(device)", tdevice).replace(
                                "$(hostname)", hostname)
                missing = []
                for var, desc in self.xmlpackage.standardComponentVariables[
                        module].items():
                    if var in self.__params.keys():
                        xml = xml.replace("$(%s)" % var, self.__params[var])
                    elif var in self.__specialparams.keys():
                        if self.__specialparams[var] is not None:
                            xml = xml.replace("$(%s)" % var,
                                              self.__specialparams[var])
                        else:
                            raise Exception(
                                "Parameter: %s cannot be found" % var)
                    elif desc["default"] is not None:
                        xml = xml.replace("$(%s)" % var, desc["default"])
                    else:
                        missing.append(var)
                if missing:
                    if sys.version_info > (3,):
                        root = et.fromstring(
                            bytes(xml, "UTF-8"),
                            parser=XMLParser(collect_ids=False))
                    else:
                        root = et.fromstring(
                            xml,
                            parser=XMLParser(collect_ids=False))
                    nodes = root.findall(".//attribute")
                    nodes.extend(root.findall(".//field"))
                    nodes.extend(root.findall(".//link"))
                    grnodes = root.findall(".//group")
                    for node in nodes:
                        text = self.__getText(node)
                        for ms in missing:
                            label = "$(%s)" % ms
                            if label in text:
                                parent = node.getparent()
                                parent.remove(node)
                                break
                    for node in grnodes:
                        text = node.attrib["name"]
                        if text and "$(" in text:
                            for ms in missing:
                                label = "$(%s)" % ms
                                if label in text:
                                    parent = node.getparent()
                                    parent.remove(node)
                                    break
                    xml = _simpletoxml(root)
                    if self._printouts:
                        print("MISSING %s" % missing)
                    errors = []
                    for var in missing:
                        if "s.$(%s)" % var in xml:
                            errors.append(var)
                    if errors:
                        print(
                            "WARNING: %s cannot be created without %s"
                            % (var, errors))
                        continue

                    for var in missing:
                        xml = xml.replace("$(%s)" % var, "")
                    lines = xml.split('\n')
                    xml = '\n'.join([x for x in lines if len(x.strip())])
                if xmlfile.endswith(".ds.xml"):
                    self._printAction(newname)
                    self.datasources[newname] = xml
                else:
                    self._printAction(newname)
                    self.components[newname] = xml

    def _printAction(self, name):
        """ prints out information about the performed action

        :param name: component name
        :type name: :obj:`str`
        """
        if self._printouts:
            if hasattr(self.options, "database") and \
               self.options.database:
                print("CREATING '%s' of '%s' on '%s' with %s" % (
                    name,
                    self.options.cptype,
                    self.options.server,
                    self.__params))
            else:
                print("CREATING '%s' of '%s' in '%s/%s%s.xml' with %s" % (
                    name,
                    self.options.cptype,
                    self.options.directory,
                    self.options.file,
                    name,
                    self.__params))

    @classmethod
    def __getText(cls, node):
        """ collects text from text child nodes

        :param node: parent node
        :type node: :obj:`xml.etree.ElementTree.Element`
        """
        if node is not None:
            tnodes = ([node.text] if node.text else []) \
                     + [child.tail for child in node if child.tail]
            return unicode("".join(tnodes)).strip()
        return ""


if __name__ == "__main__":
    pass
