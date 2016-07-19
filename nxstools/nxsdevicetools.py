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

""" NDTS TANGO device tools """

import sys
import os
import time

standardComponentVariables = {}
standardComponentTemplateFiles = {}
moduleTemplateFiles = {}
moduleMultiAttributes = {}


class PackageHandler(object):
    """ xml templates package loader
    """

    def __init__(self, packagename='nxstools.xmltemplates'):
        """ constructor

        :param packagename: full package name
        :type packagename: :obj:`str`
        """
        self.packagename = None
        self.package = None
        self.packagepath = None
        self.loadXMLTemplates(packagename)

    def loadXMLTemplates(self, packagename):
        """ load xml template module variables

        :param packagename: full package name
        :type packagename: :obj:`str`
        """
        self.packagename = packagename
        global standardComponentVariables
        global standardComponentTemplateFiles
        global moduleTemplateFiles
        global moduleMultiAttributes
        self.package = __import__(
            packagename, globals(), locals(), packagename[-1])
        standardComponentVariables = \
            self.package.standardComponentVariables
        standardComponentTemplateFiles = \
            self.package.standardComponentTemplateFiles
        moduleTemplateFiles = \
            self.package.moduleTemplateFiles
        moduleMultiAttributes = \
            self.package.moduleMultiAttributes
        self.packagepath = os.path.dirname(self.package.__file__)

xmlPackageHandler = PackageHandler()


#: attributes of device modules to acquire with elements:
#  'module': [<sardana_pool_attr>, <original_tango_attr>]
moduleAttributes = {
    'counter_tango': ['Value', 'Counts'],
    'dgg2': ['Value', 'SampleTime'],
    'mca_8701': ['Value', 'Data'],
    'mca_sis3302new': ['Value', 'Data'],
    'mca_sis3302': ['Value', 'Data'],
    'mythenroi': ['Value', None],
    'mca8715roi': ['Value', None],
    'sis3302roi': ['Value', None],
    'sis3610': ['Value', 'Value'],
    'sis3820': ['Value', 'Counts'],
    'tangoattributectctrl': ['Value', None],
    'tip551': ['Value', 'Voltage'],
    'tip830': ['Value', 'Counts'],
    'vfcadc': ['Value', 'Counts'],
    'xmcd': ['Value', None],
}


#: modules of 2d detectors
twoDModules = [
    'pilatus100k', 'pilatus300k', 'pilatus1m',
    'pilatus2m', 'pilatus6m', 'pco4000', 'perkinelmerdetector',
    'lambda', 'pedetector', 'perkinelmer',
    'pco', 'pcoedge', 'marccd', 'perkinelmer',
    #
    'lcxcamera', 'limaccd', 'eigerpsi',
    'eigerdectris'
]


#: modules of motors
motorModules = [
    'absbox', 'motor_tango', 'kohzu', 'smchydra', 'lom', 'oms58', 'e6c',
    'omsmaxv', 'spk', 'pie710', 'pie712', 'e6c_p09_eh2'
    #
    #    'analyzerep01', 'tth', 'atto300',  'phaseretarder',
    #    'hexa',
    #    'tm', 'cube', , 'piezonv40', 'smaractmcs',
    #    'slt', 'bscryotempcontrolp01',
    #    'dcm_energy', 'elom', 'diffracmu',  'tcpipmotor',
    #    'galil_dmc', 'pico8742', 'oxfcryo700ctrl', 'analyzer', 'nfpaxis',
    #    'smarpod', 'mult',
    #
    #    'oxfcryo700',
]

#: counter/timer modules
ctModules = [
    'mca8715roi', 'onedroi', 'sis3820', 'sis3302roi',
    'xmcd', 'vfcadc', 'mythenroi', 'mhzdaqp01', 'dgg2',
    'tangoattributectctrl'
]

#: modules of 0D detectors
zeroDModules = ['tip830']

#: modules of 1D detectors
oneDModules = ['mca_xia']

#: IO register modules
ioRegModules = ['sis3610']


PYTANGO = False
try:
    import PyTango
    PYTANGO = True
except:
    pass


for mn in motorModules:
    moduleAttributes[mn] = ['Position', 'Position']

for nm in ctModules + zeroDModules + oneDModules:
    if nm not in moduleAttributes:
        moduleAttributes[nm] = ['Value', None]


def generateDeviceNames(prefix, first, last, minimal=False):
    """ generates device names

    :param prefix: device name prefix
    :param first: first device index
    :param last: last device index
    :returns: device names
    """
    names = []
    if prefix.strip():
        for i in range(first, last + 1):
            if not minimal:
                names.append(prefix + ("0" if len(str(i)) == 1 else "")
                             + str(i))
            else:
                names.append(prefix + str(i))
    return names


def getAttributes(device, host=None, port=10000):
    """ provides a list of device attributes

    :param device: tango device name
    :param host: device host
    :param port: device port
    :returns: list of device attributes

    """
    if host:
        dp = PyTango.DeviceProxy("%s:%s/%s" % (host, port, device))
    else:
        dp = PyTango.DeviceProxy(device)
    attr = dp.attribute_list_query()
    return [at.name for at in attr if at.name not in ['State', 'Status']]


def openServer(device):
    """ opens connection to the configuration server

    :param configuration: server device
    :returns: configuration server proxy
    """
    found = False
    cnt = 0
    # spliting character
    try:
        #: configuration server proxy
        cnfServer = PyTango.DeviceProxy(device)
    except (PyTango.DevFailed, PyTango.Except, PyTango.DevError):
        found = True

    if found:
        sys.stderr.write(
            "Error: Cannot connect into the server: %s\n" % device)
        sys.stderr.flush()
        sys.exit(0)

    while not found and cnt < 1000:
        if cnt > 1:
            time.sleep(0.01)
        try:
            if cnfServer.state() != PyTango.DevState.RUNNING:
                found = True
        except (PyTango.DevFailed, PyTango.Except, PyTango.DevError):
            time.sleep(0.01)
            found = False
        cnt += 1

    if not found:
        sys.stderr.write("Error: Setting up %s takes to long\n" % device)
        sys.stderr.flush()
        sys.exit(0)

    return cnfServer


def storeDataSource(name, xml, server):
    """ stores datasources in Configuration Server

    :param name: datasource name
    :param xml: datasource xml string
    :param server: configuration server
    """
    proxy = openServer(server)
    proxy.Open()
    proxy.XMLString = str(xml)
    proxy.StoreDataSource(str(name))


def getServerTangoHost(server):
    """ fetches the server tango host

    :param server: tango server
    :returns: tango host
    """
    proxy = openServer(server)
    host = proxy.get_db_host()
    port = proxy.get_db_port()
    shost = str(host).split(".")
    if len(shost) > 0:
        host = shost[0]
    return "%s:%s" % (host, port)


def getDataSourceComponents(server):
    """ gets datasource components

    :param server: configuration server
    :returns: dictionary with datasource components
    """
    dscps = {}
    proxy = openServer(server)
    proxy.Open()
    acps = proxy.availableComponents()
    for cp in acps:
        try:
            dss = proxy.componentDataSources(cp)
            for ds in dss:
                if ds not in dscps:
                    dscps[ds] = []
                dscps[ds].append(cp)
        except Exception as e:
            sys.stderr.write(str(e))
            sys.stderr.write(
                "Error: Internal error of the %s component\n" % cp)
            sys.stderr.flush()
    return dscps


def storeComponent(name, xml, server):
    """ stores components in Configuration Server

    :param name: component name
    :param xml: component xml string
    :param server: configuration server
    """
    proxy = openServer(server)
    proxy.Open()
    proxy.XMLString = str(xml)
    proxy.StoreComponent(str(name))


def getClassName(devicename='NXSConfigServer'):
    """ provides device class name

    :param devicename: device name
    :returns: class name
    """
    try:
        db = PyTango.Database()
    except:
        sys.stderr.write(
            "Error: Cannot connect into %s" % devicename
            + "on host: \n    %s \n " % os.environ['TANGO_HOST'])
        sys.stderr.flush()
        return ""

    return db.get_class_for_device(devicename)


def getServers(name='NXSConfigServer'):
    """ provides server device names

    :param name: server instance name
    :returns: list of the server device names

    """
    try:
        db = PyTango.Database()
    except:
        sys.stderr.write(
            "Error: Cannot connect into %s" % name
            + "on host: \n    %s \n " % os.environ['TANGO_HOST'])
        sys.stderr.flush()
        return ""

    servers = db.get_device_exported_for_class(name).value_string
    return servers


def _remoteCall(server, func, *args, **kwargs):
    """ executes function on remove tango host db setup

    :param server: remove tango server device name
    :param func: executed function
    :param args: function list arguments
    :param kwargs: function dict arguments
    :returns: function result
    """
    lserver = None
    if server and server.strip():
        lserver = server.split("/")[0]
    if lserver:
        lserver = lserver.strip()
    if lserver:
        if ":" not in lserver:
            lserver = lserver + ":10000"
        localtango = os.environ.get('TANGO_HOST')
        os.environ['TANGO_HOST'] = lserver

    res = func(*args, **kwargs)
    if lserver and localtango is not None:
        os.environ['TANGO_HOST'] = localtango
    return res


def listServers(server, name='NXSConfigServer'):
    """ finds server names

    :param name: server instance name
    :returns: server list
    """
    return _remoteCall(server, getServers, name)


def findClassName(server, name):
    """ finds class name

    :param name: device name
    :returns: class name
    """
    return _remoteCall(server, getClassName, name)


def checkServer(name='NXSConfigServer'):
    """ provides server device name if only one or error in the other case

    :param name: server name
    :returns: server device name or empty string if error appears
    """
    servers = getServers(name)
    if not servers:
        sys.stderr.write(
            "Error: No required server on current host running. \n\n"
            + "    Please specify the server from the other host. \n\n")
        sys.stderr.flush()
        return ""
    if len(servers) > 1:
        sys.stderr.write(
            "Error: More than on %s " % name
            + "on the current host running. \n\n"
            + "    Please specify the server:"
            + "\n        %s\n\n" % "\n        ".join(servers))
        sys.stderr.flush()
        return ""
    return servers[0]


if __name__ == "__main__":
    pass
