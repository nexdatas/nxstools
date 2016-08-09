#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2016 DESY, Jan Kotanski <jkotan@mail.desy.de>
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
import os

from xml.dom.minidom import parse, parseString
from nxstools import nxsdevicetools
import nxstools.nxsdevicetools
from nxstools.nxsdevicetools import (
    storeDataSource, getDataSourceComponents, storeComponent,
    moduleAttributes, motorModules,
    moduleTemplateFiles, generateDeviceNames, getServerTangoHost,
    openServer, findClassName,
    xmlPackageHandler)
from nxstools.nxsxml import (XMLFile, NDSource, NGroup, NField, NLink,
                             NDimensions)

#: (:obj:`bool`) True if PyTango available
PYTANGO = False
try:
    import PyTango
    PYTANGO = True
except:
    pass


class CPExistsException(Exception):
    """ Component already exists exception
    """
    pass


class Device(object):
    """ device from online.xml
    """
    __slots__ = [
        'name', 'dtype', 'module', 'tdevice', 'hostname', 'sardananame',
        'sardanahostname', 'host', 'port', 'group', 'attribute']

    def __init__(self):
        #: (:obj:`str`) device name
        self.name = None
        #: (:obj:`str`) data type
        self.dtype = None
        #: (:obj:`str`) device module
        self.module = None
        #: (:obj:`str`) device type
        self.tdevice = None
        #: (:obj:`str`) host name with port
        self.hostname = None
        #: (:obj:`str`) sardana name with port
        self.sardananame = None
        #: (:obj:`str`) sardana host name
        self.sardanahostname = None
        #: (:obj:`str`) host without port
        self.host = None
        #: (:obj:`str`) tango port
        self.port = None
        #: (:obj:`str`) datasource tango group
        self.group = None
        #: (:obj:`str`) attribute name
        self.attribute = None

    def tolower(self):
        """ converts `name`, `module`, `tdevice`, `hostname` into lower case
        """
        self.name = self.name.lower()
        self.module = self.module.lower()
        self.tdevice = self.tdevice.lower()
        self.hostname = self.hostname.lower()

    def splitHostPort(self):
        """ spilts host name from port
        """
        if self.hostname:
            self.host = self.hostname.split(":")[0]
            self.port = self.hostname.split(":")[1] \
                if len(self.hostname.split(":")) > 1 else None
        else:
            self.host = None
            self.port = None
            raise Exception("hostname not defined")

    def findAttribute(self, tangohost):
        """ sets attribute and datasource group of online.xml device

        :param tangohost: tango host
        :type tangohost: :obj:`str`
        """
        mhost = self.sardanahostname or tangohost
        self.group = None
        self.attribute = None
        # if module.lower() in motorModules:
        if self.module in motorModules:
            self.attribute = 'Position'
        elif self.dtype == 'stepping_motor':
            self.attribute = 'Position'
        elif PYTANGO and self.module in moduleAttributes:
            try:
                dp = PyTango.DeviceProxy(str("%s/%s" % (mhost, self.name)))
                mdevice = str(dp.name())

                sarattr = moduleAttributes[self.module][0]
                if not sarattr or \
                   sarattr not in dp.get_attribute_list():
                    raise Exception("Missing attribute: Value")
                self.hostname = mhost
                self.host = mhost.split(":")[0]
                if len(mhost.split(":")) > 1:
                    self.port = mhost.split(":")[1]

                self.tdevice = mdevice
                self.attribute = sarattr
                self.group = '__CLIENT__'
            except Exception:
                if moduleAttributes[self.module][1]:
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
    def _createTangoDataSource(
            cls, name, directory, fileprefix, server, device,
            attribute, host, port="10000", group=None):
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
        :param attribute: attribute name
        :type attribute: :obj:`str`
        :param host: tango host name
        :type host: :obj:`str`
        :param port: tango port
        :type port: :obj:`str`
        :parma group: datasource tango group
        :type group: :obj:`str`
        :returns: xml string
        :rtype: :obj:`str`
        """
        df = XMLFile("%s/%s%s.ds.xml" % (directory, fileprefix, name))
        sr = NDSource(df)
        sr.initTango(name, device, "attribute", attribute, host, port,
                     group=group)
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
        print "%s/%s%s.ds.xml" % (directory, fileprefix, dname)
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
                     strategy, units, link, chunk):
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
            field.setStrategy(strategy)
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

    @classmethod
    def _createComponent(cls, name, directory, fileprefix, nexuspath,
                         strategy, nexusType, units, links, server, chunk):
        """ creates component file

        :param name: datasource name
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
        """
        defpath = '/entry$var.serialno:NXentry/instrument' \
                  + '/collection/%s' % (name)
        df = XMLFile("%s/%s%s.xml" % (directory, fileprefix, name))
        cls.__createTree(df, nexuspath or defpath, name, nexusType,
                         strategy, units, links, chunk)

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
        :type node: :class:`xml.dom.minidom.Node`
        :returns: xml content string
        :rtype: :obj:`str`
        """
        if not node:
            return
        xml = node.toxml()
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
        :type parent: :class:`xml.dom.minidom.Node`
        :param childname: child name
        :type childname: :opj:`str`
        :returns: text string
        :rtype: :obj:`str`
        """
        return cls._getText(
            parent.getElementsByTagName(childname)[0]) \
            if len(parent.getElementsByTagName(childname)) else None


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
            except:
                raise WrongParameterError(
                    "CollCompCreator Invalid --first parameter\n")

            try:
                last = int(self.options.last)
            except:
                raise WrongParameterError(
                    "CollCompCreator Invalid --last parameter\n")
            aargs = generateDeviceNames(self.options.device, first, last,
                                        self.options.minimal)

        self.args += aargs
        if not len(self.args):
            raise WrongParameterError("")

        for name in self.args:
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
                self.options.chunk)


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
                first = int(self.options.first)
            except:
                raise WrongParameterError(
                    "TangoDSCreator: Invalid --first parameter\n")
            try:
                last = int(self.options.last)
            except:
                raise WrongParameterError(
                    "TangoDSCreator: Invalid --last parameter\n")

            dvargs = generateDeviceNames(self.options.device, first, last)
            dsargs = generateDeviceNames(self.options.datasource, first, last)

        if not dvargs or not len(dvargs):
            raise WrongParameterError("")

        for i in range(len(dvargs)):
            if not self.options.database:
                print "CREATING %s: %s%s.ds.xml" % (
                    dvargs[i], self.options.file, dsargs[i])
            else:
                print "STORING %s: %s" % (dvargs[i], dsargs[i])
            self._createTangoDataSource(
                dsargs[i], self.options.directory, self.options.file,
                self.options.server if self.options.database else None,
                dvargs[i],
                self.options.attribute,
                self.options.host,
                self.options.port)


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
            except:
                raise WrongParameterError(
                    "ClientDSCreator: Invalid --first parameter\n")
            try:
                last = int(self.options.last)
            except:
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
            else:
                print("CREATING %s %s/%s %s" % (
                    dv.name + ":" + " " * (34 - len(dv.name)),
                    dv.hostname,
                    dv.tdevice + " " * (
                        60 - len(dv.tdevice) - len(dv.hostname)),
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
            for dsname, dsxml in self.datasources.items():
                storeDataSource(dsname, dsxml, server)
        else:
            for dsname, dsxml in self.datasources.items():
                myfile = open("%s/%s%s.ds.xml" % (
                    self.options.directory,
                    self.options.file, dsname), "w")
                myfile.write(dsxml)
                myfile.close()

    def createXMLs(self):
        """ creates datasource xmls of all online.xml simple devices
        """
        self.datasources = {}
        tangohost = getServerTangoHost(self.options.server)
        indom = parse(self.args[0])
        hw = indom.getElementsByTagName("hw")
        device = hw[0].firstChild
        dscps = {}
        if self._printouts and not hasattr(self.options, "directory") or \
           not self.options.directory:
            try:
                dscps = getDataSourceComponents(self.options.server)
            except Exception:
                dscps = {}

        while device:
            if device.nodeName == 'device':
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
                except:
                    if self._printouts:
                        print("ERROR %s: host for module %s of %s "
                              "type not defined"
                              % (dv.name, dv.module, dv.dtype))
                    device = device.nextSibling
                    continue
                dv.findAttribute(tangohost)
                if dv.attribute:
                    dv.setSardanaName(self.options.lower)
                    self._printAction(dv, dscps)
                    xml = self._createTangoDataSource(
                        dv.name, None, None, None,
                        dv.tdevice, dv.attribute, dv.host, dv.port, dv.group)
                    self.datasources[dv.name] = xml
                if (dv.module in
                    self.xmlpackage.moduleMultiAttributes.keys()) or (
                        dv.module == 'module_tango'
                        and len(dv.tdevice.split('/')) == 3
                        and dv.tdevice.split('/')[1]
                        in self.xmlpackage.moduleMultiAttributes.keys()):
                    if dv.module == 'module_tango':
                        module = dv.tdevice.split('/')[1]
                    else:
                        module = dv.module
                    multattr = self.xmlpackage.moduleMultiAttributes[
                        module.lower()]
                    for at in multattr:
                        dsname = "%s_%s" % (dv.name.lower(), at.lower())
                        xml = self._createTangoDataSource(
                            dsname, None, None, None,
                            dv.tdevice, at, dv.host, dv.port,
                            "%s_" % (dv.name.lower()))
                        self.datasources[dsname] = xml
                        mdv = copy.copy(dv)
                        mdv.name = dsname
                        self._printAction(mdv, dscps)
                elif not dv.attribute:
                    if self._printouts:
                        print(
                            "SKIPPING %s:    module %s of %s type not defined"
                            % (dv.name, dv.module, dv.dtype))
            device = device.nextSibling


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
        #: (:obj:`str`) xml template component package path
        self.xmltemplatepath = xmlPackageHandler.packagepath
        #: (:obj:`str`) xml template component package
        self.xmlpackage = xmlPackageHandler.package

    def create(self):
        """ creates components of all online.xml complex devices
        """
        cpname = self.options.component
        if not hasattr(self.options, "directory") or \
           not self.options.directory:
            server = self.options.server
            if not self.options.overwrite:
                try:
                    proxy = openServer(server)
                    proxy.Open()
                    acps = proxy.availableComponents()
                except:
                    raise Exception("Cannot connect to %s" % server)

                if cpname in acps or (
                        self.options.lower and cpname.lower() in acps):
                    raise CPExistsException(
                        "Component '%s' already exists." % cpname)

        self.createXMLs()
        server = self.options.server
        if not hasattr(self.options, "directory") or \
           not self.options.directory:
            for dsname, dsxml in self.datasources.items():
                storeDataSource(dsname, dsxml, server)
            for cpname, cpxml in self.components.items():
                storeComponent(cpname, cpxml, server)
        else:
            for dsname, dsxml in self.datasources.items():
                myfile = open("%s/%s%s.ds.xml" % (
                    self.options.directory,
                    self.options.file, dsname), "w")
                myfile.write(dsxml)
                myfile.close()
            for cpname, cpxml in self.components.items():
                myfile = open("%s/%s%s.xml" % (
                    self.options.directory,
                    self.options.file, cpname), "w")
                myfile.write(cpxml)
                myfile.close()

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


class OnlineCPCreator(CPCreator):

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
            if hasattr(self.options, "directory") and \
               self.options.directory:
                print("CREATING %s: %s/%s%s.ds.xml" % (
                    dv.tdevice, self.options.directory, self.options.file,
                    dv.name))
            else:
                print("CREATING %s %s/%s %s" % (
                    dv.name + ":" + " " * (34 - len(dv.name)),
                    dv.hostname,
                    dv.tdevice + " " * (
                        60 - len(dv.tdevice) - len(dv.hostname)),
                    ",".join(dscps[dv.name])
                    if (dscps and dv.name in dscps and dscps[dv.name])
                    else ""))

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
                if device.module.lower() == 'module_tango' \
                   and len(device.tdevice.split('/')) == 3 \
                   and device.tdevice.split('/')[1] \
                   in self.xmlpackage.moduleMultiAttributes.keys():
                    return device.tdevice.split('/')[1].lower()
            except:
                return

    def listcomponents(self):
        """ provides a list of components with xml templates

        :returns: list of components with xml templates
        :rtype: :obj:`list` <:obj:`str` >
        """
        indom = parse(self.args[0])
        hw = indom.getElementsByTagName("hw")
        device = hw[0].firstChild
        cpnames = set()

        while device:
            if device.nodeName == 'device':
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

                module = self._getModuleName(dv)
                if module:
                    if module.lower() in self.xmlpackage.moduleTemplateFiles:
                        cpnames.add(dv.name)
            device = device.nextSibling
        return cpnames

    def createXMLs(self):
        """ creates component xmls of all online.xml complex devices
        """
        self.datasources = {}
        self.components = {}
        indom = parse(self.args[0])
        hw = indom.getElementsByTagName("hw")
        device = hw[0].firstChild
        cpname = self.options.component

        while device:
            if device.nodeName == 'device':
                name = self._getChildText(device, "name")
                if self.options.lower:
                    name = name.lower()
                    cpname = cpname.lower()
                if name == cpname:
                    dv = Device()
                    dv.name = name
                    dv.dtype = self._getChildText(device, "type")
                    dv.module = self._getChildText(device, "module")
                    dv.tdevice = self._getChildText(device, "device")
                    dv.hostname = self._getChildText(device, "hostname")
                    dv.sardananame = self._getChildText(device, "sardananame")
                    dv.sardanahostname = self._getChildText(
                        device, "sardanahostname")

                    try:
                        dv.splitHostPort()
                    except:
                        if self._printouts:
                            print("ERROR %s: host for module %s of %s "
                                  "type not defined"
                                  % (dv.name, dv.module, dv.dtype))
                        device = device.nextSibling
                        continue
                    module = self._getModuleName(dv)
                    if module:
                        multattr = self.xmlpackage.moduleMultiAttributes[
                            module.lower()]
                        for at in multattr:
                            dsname = "%s_%s" % (dv.name.lower(), at.lower())
                            xml = self._createTangoDataSource(
                                dsname, None, None, None,
                                dv.tdevice, at, dv.host, dv.port,
                                "%s_" % (dv.name.lower()))
                            self.datasources[dsname] = xml
                            mdv = copy.copy(dv)
                            mdv.name = dsname
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
                                xml = xmlcontent.replace("$(name)", cpname)
                                mdv = copy.copy(dv)
                                mdv.name = newname
                                self._printAction(mdv)
                                if xmlfile.endswith(".ds.xml"):
                                    self.datasources[newname] = xml
                                else:
                                    self.components[newname] = xml

            device = device.nextSibling


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
        return self.xmlpackage.standardComponentVariables.keys()

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
                 self.xmlpackage.standardComponentVariables.keys()))
        return self.xmlpackage.standardComponentVariables[
            self.options.cptype]

    def __setspecialparams(self):
        """ sets special parameters, 
        i.e. __tangohost__, __tangoport__ and __configdevice__
        
        """
        server = self.options.server
        host, port = getServerTangoHost(server).split(":")
        self.__specialparams['__tangohost__'] = host
        self.__specialparams['__tangoport__'] = port
        proxy = openServer(server)
        self.__specialparams['__configdevice__'] = proxy.name()

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
                (module, self.xmlpackage.standardComponentVariables.keys()))

        if module in self.xmlpackage.standardComponentTemplateFiles:
            xmlfiles = self.xmlpackage.standardComponentTemplateFiles[module]
        else:
            xmlfiles = ["%s.xml" % module]
        for xmlfile in xmlfiles:
            newname = self._replaceName(xmlfile, cpname, module)
            with open(
                    '%s/%s' % (
                        self.xmltemplatepath, xmlfile), "r"
            ) as content_file:
                xmlcontent = content_file.read()
                xml = xmlcontent.replace("$(name)", cpname)
                missing = []
                for var, desc in self.xmlpackage.standardComponentVariables[
                        module].items():
                    if var in self.__params.keys():
                        xml = xml.replace("$(%s)" % var, self.__params[var])
                    elif var in self.__specialparams.keys():
                        xml = xml.replace("$(%s)" % var,
                                          self.__specialparams[var])
                    elif desc["default"] is not None:
                        xml = xml.replace("$(%s)" % var, desc["default"])
                    else:
                        missing.append(var)
                if missing:
                    indom = parseString(xml)
                    nodes = indom.getElementsByTagName("attribute")
                    nodes.extend(indom.getElementsByTagName("field"))
                    for node in nodes:
                        text = self.__getText(node)
                        for ms in missing:
                            label = "$(%s)" % ms
                            if label in text:
                                parent = node.parentNode
                                parent.removeChild(node)
                                break
                    xml = indom.toxml()
                    if self._printouts:
                        print("MISSING %s" % missing)
                    for var in missing:
                        xml = xml.replace("$(%s)" % var, "")
                    lines = xml.split('\n')
                    xml = '\n'.join(filter(lambda x: len(x.strip()), lines))
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
            if hasattr(self.options, "directory") and \
               self.options.directory:
                print("CREATING '%s' of '%s' in '%s/%s%s.xml' with %s" % (
                    name,
                    self.options.cptype,
                    self.options.directory,
                    self.options.file,
                    self.options.component,
                    self.__params))
            else:
                print("CREATING '%s' of '%s' on '%s' with %s" % (
                    name,
                    self.options.cptype,
                    self.options.server,
                    self.__params))

    @classmethod
    def __getText(cls, node):
        """ collects text from text child nodes

        :param node: parent node
        :type node: :obj:`xml.dom.minidom.Node`
        :returns: node content text
        :rtype: :obj:`str`
        """
        text = ""
        if node:
            child = node.firstChild
            while child:
                if child.nodeType == child.TEXT_NODE:
                    text += child.data
                child = child.nextSibling
        return text

if __name__ == "__main__":
    pass
