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

""" Set Up NeXus Tango Servers"""

import socket
import os
import sys
import time
import json
import argparse
import subprocess

try:
    import tango
except Exception:
    import PyTango as tango

from nxstools.nxsargparser import (Runner, NXSArgParser, ErrorException)

#: (:obj:`str`) host name
_hostname = socket.gethostname()


#: (:obj:`dict` <:obj:`dict` <:obj:`str` , :obj:`str` > > )
#:    all SardanaHosts and DataBaseHosts should be known
knownHosts = {
    'hasdelay': {'beamline': 'delay', 'masterhost': 'hasdelay',
                 'user': 'delayusr', 'dbname': 'nxsconfig'},
    'hasdelay2': {'beamline': 'delsauto', 'masterhost': 'hasdelay2',
                  'user': 'delayusr', 'dbname': 'nxsconfig'},
    'hasfpgm1': {'beamline': 'flash', 'masterhost': 'hasfpgm1',
                 'user': 'vuvfuser', 'dbname': 'nxsconfig'},
    'hasfvls': {'beamline': 'flash', 'masterhost': 'hasfvls',
                'user': 'vuvfuser', 'dbname': 'nxsconfig'},
    'hasfmirr': {'beamline': 'flash', 'masterhost': 'hasfmirr',
                 'user': 'musixusr', 'dbname': 'nxsconfig'},
    'haskmusixtng': {'beamline': 'flash', 'masterhost': 'haskmusixtng',
                     'user': 'vuvfuser', 'dbname': 'nxsconfig'},
    'hasmfmc': {'beamline': 'fmc', 'masterhost': 'hasmfmc',
                'user': 'delayusr', 'dbname': 'nxsconfig'},
    'hasmlqj': {'beamline': 'lqj', 'masterhost': 'hasmlqj',
                'user': 'lqjuser', 'dbname': 'nxsconfig'},
    # ? 'haso052metro': {'beamline': 'metro', 'masterhost': 'haso052metro',
    # ?            'user': '???', 'dbname': 'nxsconfig'},
    'hasodlsauto': {'beamline': 'dlsauto', 'masterhost': 'hasodlsauto',
                    'user': 'dlsuser', 'dbname': 'nxsconfig'},
    'haso111n': {'beamline': 'p09', 'masterhost': 'haso111n',
                 'user': 'tnunez', 'dbname': 'nxsconfig'},
    'haso111tb': {'beamline': 'p09', 'masterhost': 'haso111tb',
                  'user': 'tnunez', 'dbname': 'nxsconfig'},
    'haso113b': {'beamline': 'p09', 'masterhost': 'haso113b',
                 'user': 'blume', 'dbname': 'nxsconfig'},
    'haso111o': {'beamline': 'p09'},  # Benjamin Obuna
    'haso113u': {'beamline': 'p09', 'masterhost': 'haso113u',
                 'user': 'kracht', 'dbname': 'nxsconfig'},
    'hastodt': {'beamline': 'p09', 'masterhost': 'hastodt',
                'user': 'kracht', 'dbname': 'nxsconfig'},
    'haso204n': {'beamline': 'p23', 'masterhost': 'haso204n',
                 'user': 'p23user', 'dbname': 'nxsconfig'},
    'haso228jk': {'beamline': 'p09', 'masterhost': 'haso228jk',
                  'user': 'jkotan', 'dbname': 'nxsconfig'},
    'haso213p': {'beamline': 'p22', 'masterhost': 'haso213p',
                 'user': 'spiec', 'dbname': 'nxsconfig'},
    'has6117b': {'beamline': 'p02', 'masterhost': 'has6117b',
                 'user': 'p02user', 'dbname': 'nxsconfig'},
    'haspecsicl4': {'beamline': 'p02', 'masterhost': 'haspecsicl4',
                    'user': 'lacluser', 'dbname': 'nxsconfig'},
    'haspllabcl1': {'beamline': 'llab', 'masterhost': 'haspllabcl1',
                    'user': 'lacluser', 'dbname': 'nxsconfig'},
    # ?'hasp144p': {'beamline': 'p11', 'masterhost': 'hasp144p',
    # ?               'user': '???', 'dbname': 'nxsconfig'},
    'haspp01eh1': {'beamline': 'p01', 'masterhost': 'haspp01eh1',
                   'user': 'p01user', 'dbname': 'nxsconfig'},
    'haspp01eh2': {'beamline': 'p01', 'masterhost': 'haspp01eh2',
                   'user': 'p01user', 'dbname': 'nxsconfig'},
    'haspp01eh3': {'beamline': 'p01', 'masterhost': 'haspp01eh3',
                   'user': 'p01user', 'dbname': 'nxsconfig'},
    'haspp02ch1a': {'beamline': 'p02', 'masterhost': 'haspp02ch1a',
                    'user': 'p02user', 'dbname': 'nxsconfig'},
    'haspp021ch1a': {'beamline': 'p021', 'masterhost': 'haspp021ch1a',
                     'user': 'p021user', 'dbname': 'nxsconfig'},
    'haspp02ch1': {'beamline': 'p02', 'masterhost': 'haspp02ch1',
                   'user': 'p02user', 'dbname': 'nxsconfig'},
    'haspp021ch1': {'beamline': 'p02', 'masterhost': 'haspp021ch1',
                    'user': 'p021user', 'dbname': 'nxsconfig'},
    'haspp02ch2': {'beamline': 'p02', 'masterhost': 'haspp02ch2',
                   'user': 'p02user', 'dbname': 'nxsconfig'},
    'haspp02oh1': {'beamline': 'p02', 'masterhost': 'haspp02oh1',
                   'user': 'p02user', 'dbname': 'nxsconfig'},
    'haspp02lakl': {'beamline': 'p02', 'masterhost': 'haspp02lakl',
                    'user': 'p02user', 'dbname': 'nxsconfig'},
    'haspp022ch': {'beamline': 'p022', 'masterhost': 'haspp022ch',
                   'user': 'p022user', 'dbname': 'nxsconfig'},
    'haspp022chms': {'beamline': 'p022', 'masterhost': 'haspp022chms',
                     'user': 'p022user', 'dbname': 'nxsconfig'},
    'haso224w': {'beamline': 'p02', 'masterhost': 'haso224w',
                 'user': 'p021user', 'dbname': 'nxsconfig'},
    'haso232s': {'beamline': 'p02', 'masterhost': 'haspp232s',
                 'user': 'p02user', 'dbname': 'nxsconfig'},
    'haspp021jenkins': {'beamline': 'p021', 'masterhost': 'haspp021jenkins',
                        'user': 'p021user', 'dbname': 'nxsconfig'},
    'haspp03': {'beamline': 'p03', 'masterhost': 'haspp03',
                'user': 'p03user', 'dbname': 'nxsconfig'},
    'haspp03nano': {'beamline': 'p03nano', 'masterhost': 'haspp03nano',
                    'user': 'p03nano', 'dbname': 'nxsconfig'},
    'haspp04exp1': {'beamline': 'p04', 'masterhost': 'haspp04exp1',
                    'user': 'p04user', 'dbname': 'nxsconfig'},
    'haspp04exp2': {'beamline': 'p04', 'masterhost': 'haspp04exp2',
                    'user': 'p04user', 'dbname': 'nxsconfig'},
    'haspp06ctrl': {'beamline': 'p06', 'masterhost': 'haspp06ctrl',
                    'user': 'p06user', 'dbname': 'nxsconfig'},
    'haspp06mc01': {'beamline': 'p06', 'masterhost': 'haspp06mc01',
                    'user': 'p06user', 'dbname': 'nxsconfig'},
    'haspp06nc1': {'beamline': 'p06', 'masterhost': 'haspp06nc1',
                   'user': 'p06user', 'dbname': 'nxsconfig'},
    'hasp029rack': {'beamline': 'p06', 'masterhost': 'hasp029rack',
                    'user': 'p06user', 'dbname': 'nxsconfig'},
    'hasp068xlab': {'beamline': 'p06', 'masterhost': 'hasp068xlab',
                    'user': 'p06user', 'dbname': 'nxsconfig'},
    'haspp07eh2': {'beamline': 'p07', 'masterhost': 'haspp07eh2',
                   'user': 'p07user', 'dbname': 'nxsconfig'},
    'haspp08': {'beamline': 'p08', 'masterhost': 'haspp08',
                'user': 'p08user', 'dbname': 'nxsconfig'},
    'haspp08lisa2': {'beamline': 'p08', 'masterhost': 'haspp08lisa2',
                     'user': 'p08user', 'dbname': 'nxsconfig'},
    'haspp09': {'beamline': 'p09', 'masterhost': 'haspp09',
                'user': 'p09user', 'dbname': 'nxsconfig'},
    'haspp09dif': {'beamline': 'p09', 'masterhost': 'haspp09dif',
                   'user': 'p09user', 'dbname': 'nxsconfig'},
    'haspp09mag': {'beamline': 'p09', 'masterhost': 'haspp09mag',
                   'user': 'p09user', 'dbname': 'nxsconfig'},
    'haspp09haxps': {'beamline': 'p09', 'masterhost': 'haspp09maxps',
                     'user': 'p09haxps', 'dbname': 'nxsconfig'},
    'haspp10e1': {'beamline': 'p10', 'masterhost': 'haspp10e1',
                  'user': 'p10user', 'dbname': 'nxsconfig'},
    'haspp10e2': {'beamline': 'p10', 'masterhost': 'haspp10e2',
                  'user': 'p10user', 'dbname': 'nxsconfig'},
    'haspp10lcx': {'beamline': 'p10', 'masterhost': 'haspp10lcx',
                   'user': 'p10user', 'dbname': 'nxsconfig'},
    'haspp10lab': {'beamline': 'p10', 'masterhost': 'haspp10lab',
                   'user': 'p10user', 'dbname': 'nxsconfig'},
    'haspp11oh': {'beamline': 'p11', 'masterhost': 'haspp11oh',
                  'user': 'p11user', 'dbname': 'nxsconfig'},
    'haspp11sardana': {'beamline': 'p11',
                       'masterhost': 'haspp11sardana',
                       'user': 'p11user', 'dbname': 'nxsconfig'},
    'haspp11user02': {'beamline': 'p11', 'masterhost': 'haspp11user02',
                      'user': 'p11user', 'dbname': 'nxsconfig'},
    'hasep212lab': {'beamline': 'p21', 'masterhost': 'hasep212lab',
                    'user': 'p212user', 'dbname': 'nxsconfig'},
    'haspp21eh2': {'beamline': 'p21', 'masterhost': 'hasep21eh2',
                   'user': 'p21user', 'dbname': 'nxsconfig'},
    'haspp21eh3': {'beamline': 'p21', 'masterhost': 'hasep21eh3',
                   'user': 'p21user', 'dbname': 'nxsconfig'},
    'haspp212oh': {'beamline': 'p21', 'masterhost': 'hasep212oh',
                   'user': 'p21user', 'dbname': 'nxsconfig'},
    'haspp21lab': {'beamline': 'p21', 'masterhost': 'haspp21lab',
                   'user': 'p21user', 'dbname': 'nxsconfig'},
    'hasep211eh': {'beamline': 'p211', 'masterhost': 'hasep211eh',
                   'user': 'p211user', 'dbname': 'nxsconfig'},
    'hasep212oh': {'beamline': 'p21', 'masterhost': 'hasep212oh',
                   'user': 'p212user', 'dbname': 'nxsconfig'},
    'hasep22oh': {'beamline': 'p22', 'masterhost': 'hasep22oh',
                  'user': 'p22user', 'dbname': 'nxsconfig'},
    'hasep22ch1': {'beamline': 'p22', 'masterhost': 'hasep22ch1',
                   'user': 'p22user', 'dbname': 'nxsconfig'},
    'hasep22ch2': {'beamline': 'p22', 'masterhost': 'hasep22ch2',
                   'user': 'p22user', 'dbname': 'nxsconfig'},
    'hasep23dev': {'beamline': 'p23', 'masterhost': 'hasep23dev',
                   'user': 'p23user', 'dbname': 'nxsconfig'},
    'hasep23eh': {'beamline': 'p23', 'masterhost': 'hasep23eh',
                  'user': 'p23user', 'dbname': 'nxsconfig'},
    # 'hasep23oh': {'beamline': 'p23', 'masterhost': 'hasep23oh',
    #               'user': 'p23user', 'dbname': 'nxsconfig'},
    'hasep23ch': {'beamline': 'p23', 'masterhost': 'hasep23ch',
                  'user': 'p23user', 'dbname': 'nxsconfig'},
    #  ? 'hase027n': {'beamline': 'p24'},
    'hasep24': {'beamline': 'p24', 'masterhost': 'hasep24',
                'user': 'p24user', 'dbname': 'nxsconfig'},
    'hasep24eh1': {'beamline': 'p24', 'masterhost': 'hasep24eh1',
                   'user': 'p24user', 'dbname': 'nxsconfig'},
    'haso107klx': {'beamline': 'p09', 'masterhost': 'haso107klx',
                   'user': 'kracht', 'dbname': 'nxsconfig'},
    'haso107d1': {'beamline': 'p09', 'masterhost': 'haso107d1',
                  'user': 'kracht', 'dbname': 'nxsconfig'},
    'haso107tk': {'beamline': 'p09', 'masterhost': 'haso107tk',
                  'user': 'kracht', 'dbname': 'nxsconfig'},
    # ? 'vbtkdesy': {'beamline': 'p09'},
    # ? 'vbtkhome': {'beamline': 'p09'},
    'hascmexp': {'beamline': 'cmexp', 'masterhost': 'hascmexp',
                 'user': 'cmexp', 'dbname': 'nxsconfig'},
    'hasnp61ch1': {'beamline': 'p61', 'masterhost': 'hasnp61ch1',
                   'user': 'p61user', 'dbname': 'nxsconfig'},
    'hasnp64': {'beamline': 'p64', 'masterhost': 'hasnp64',
                'user': 'p64user', 'dbname': 'nxsconfig'},
    'hasnp64oh': {'beamline': 'p64', 'masterhost': 'hasnp64oh',
                  'user': 'p64user', 'dbname': 'nxsconfig'},
    'hasnp65': {'beamline': 'p65', 'masterhost': 'hasnp65',
                'user': 'p65user', 'dbname': 'nxsconfig'},
    'hasnp66': {'beamline': 'p66', 'masterhost': 'hasnp66',
                'user': 'p66user', 'dbname': 'nxsconfig'},
    'hzgpp07eh1': {'beamline': 'p07', 'masterhost': 'hzgpp07eh1',
                   'user': 'p07user', 'dbname': 'nxsconfig'},
    'hzgpp07eh3': {'beamline': 'p07', 'masterhost': 'hzgpp07eh3',
                   'user': 'p07user', 'dbname': 'nxsconfig'},
    'hzgpp07eh4': {'beamline': 'p07', 'masterhost': 'hzgpp07eh4',
                   'user': 'p07user', 'dbname': 'nxsconfig'},
    'cfeld-pcx27083': {'beamline': 'cfeld', 'masterhost': 'cfeld-pcx27083',
                       'user': 'ritzkowf', 'dbname': 'nxsconfig'},
    'hasmrixs': {'beamline': 'rix', 'masterhost': 'hasmrixs',
                 'user': 'rixuser', 'dbname': 'nxsconfig'},
}


class SetUp(object):

    """ setup NXSDataWriter, NXSConfigServer and NXSRecSelector Tango servers
    """

    def __init__(self):
        """ constructor
        """
        try:
            #: (:class:`tango.Database`) tango database server
            self.db = tango.Database()
        except Exception:
            print("Can't connect to tango database on %s" %
                  os.getenv('TANGO_HOST'))
            sys.exit(255)

        #: (:obj:`str`) NeXus writer device name
        self.writer_name = None
        #: (:obj:`str`) NeXus config server device name
        self.cserver_name = None

    def changeRecorderPath(self, path, instance=None):
        """ adds a new recorder path

        :param path: new recorder path
        :type path: :obj:`str`
        :param instance: MacroServer instance name
        :type instance: :obj:`str`
        :returns: True if record path was added
        :rtype: :obj:`bool`
        """
        res = False
        if not os.path.isdir(path):
            return res
        instance = instance or "*"

        mss = self.db.get_server_list("MacroServer/%s" % instance).value_string
        for ms in mss:
            devserv = self.db.get_device_class_list(ms).value_string
            dev = devserv[0::2]
            serv = devserv[1::2]
            for idx, ser in enumerate(serv):
                if ser == 'MacroServer':
                    if dev[idx]:
                        recorderpaths = self.db.get_device_property(
                            dev[idx], "RecorderPath")["RecorderPath"]
                        if recorderpaths:
                            recorderpaths = [p for p in recorderpaths if p]
                        else:
                            recorderpaths = []
                        if path not in recorderpaths:
                            recorderpaths.append(path)
                            self.db.put_device_property(
                                dev[idx],
                                {"RecorderPath": recorderpaths})
                            res = True
        # time.sleep(0.2)
        return res

    def changePropertyName(self, server, oldname, newname, sclass=None):
        """ changes property name

        :param server: server name
        :type server: :obj:`str`
        :param oldname: old property name
        :type oldname: :obj:`str`
        :param newname: new property name
        :type newname: :obj:`str`
        :param sclass: server class name
        :type sclass: :obj:`str`
        :returns: True if property name was changed
        :rtype: :obj:`bool`

        """
        ssvr = server.split("/")
        sclass = sclass or ssvr[0]
        if len(ssvr) == 1:
            server = "%s/*" % server
        res = False
        mss = self.db.get_server_list(server).value_string
        for ms in mss:
            devserv = self.db.get_device_class_list(ms).value_string
            dev = devserv[0::2]
            serv = devserv[1::2]
            for idx, ser in enumerate(serv):
                if ser == sclass:
                    if dev[idx]:
                        if not self.db.get_device_property(
                                dev[idx], newname)[newname]:
                            oldprop = self.db.get_device_property(
                                dev[idx], oldname)[oldname]
                            if oldprop:
                                oldprop = [p for p in oldprop if p]
                                self.db.put_device_property(
                                    dev[idx],
                                    {newname: oldprop})
                                self.db.delete_device_property(
                                    dev[idx], oldname)
                                res = True
        time.sleep(0.2)
        return res

    def changePropertyValue(self, server, newname, newvalue, sclass=None):
        """ changes/sets property value

        :param server: server name
        :type server: :obj:`str`
        :param newvalue: new property value
        :type newvalue: :obj:`str`
        :param newname: new property name
        :type newname: :obj:`str`
        :param sclass: server class name
        :type sclass: :obj:`str`
        :returns: True if property name was changed
        :rtype: :obj:`bool`

        """
        if "/" in server:
            sclass = sclass or server.split("/")[0]
            fserver = server
        else:
            sclass = sclass or server
            fserver = "%s/*" % server
        res = False
        value = json.loads(newvalue)
        mss = self.db.get_server_list(fserver).value_string
        for ms in mss:
            devserv = self.db.get_device_class_list(ms).value_string
            dev = devserv[0::2]
            serv = devserv[1::2]
            for idx, ser in enumerate(serv):
                if ser == sclass:
                    if dev[idx]:
                        if value:
                            value = [p for p in value if p]
                            self.db.put_device_property(
                                dev[idx],
                                {newname: value})
                            res = True
        time.sleep(0.2)
        return res

    def getStarterName(self, host):
        """ restarts server

        :param host: server host name
        :type host: :obj:`str`
        :returns: starter device name
        :rtype: :obj:`str`
        """
        admin = None
        if not host:
            host = socket.gethostname()
        admins = self.db.get_device_exported_for_class(
            "Starter").value_string
        eadmins = [adm for adm in admins
                   if self.db.get_device_exported(adm).value_string]
        if len(eadmins) == 1:
            admin = eadmins[0]
        elif len(eadmins) > 1:
            if 'tango/admin/%s' % host in eadmins:
                admin = 'tango/admin/%s' % host
            else:
                admin = eadmins[0]
        return admin

    def waitServerNotRunning(self, server=None, device=None,
                             adminproxy=None,
                             maxcnt=10000, verbose=True,
                             waitforproc=True):
        """  wait until device is exported and server is running

        :param server: server name, check if running when not None
        :type server: :obj:`str`
        :param device: device name, check if exported when not None
        :type device: :obj:`str`
        :param adminproxy: Starter device proxy
        :type adminproxy: :obj:`tango.DeviceProxy`
        :param maxcnt: maximal waiting time in 10ms
        :type maxcnt: :obj:`int`
        :param verbose: verbose mode
        :type verbose: :obj:`bool`
        :param waitforproc: wait for process list update
        :type waitforporc: :obj:`bool`
        :returns: True if server is running
        :rtype: :obj:`bool`
        """
        found = True
        cnt = 0
        running = True
        while found and cnt < maxcnt:
            try:
                if server and adminproxy is not None and running:
                    if verbose:
                        sys.stdout.write(".")
                        sys.stdout.flush()
                    adminproxy.UpdateServersInfo()
                    # running = adminproxy.RunningServers
                    running = adminproxy.DevGetRunningServers(True)
                    if server in running:
                        time.sleep(0.02)
                        cnt += 1
                        continue
                    else:
                        running = False
                if device:
                    if verbose:
                        sys.stdout.write(".")
                        sys.stdout.flush()
                    exl = self.db.get_device_exported(device)
                    if device in exl.value_string:
                        time.sleep(0.02)
                        cnt += 1
                        continue
                found = False
                if verbose:
                    if device or server:
                        print(" %s is not working" % (device or server))
            except Exception as e:
                print(str(e))
                time.sleep(0.02)
                found = True
            cnt += 1
        if waitforproc:
            time.sleep(1.5)
        return found

    def waitServerRunning(self, server=None, device=None,
                          adminproxy=None,
                          maxcnt=10000, verbose=True,
                          waitforproc=True):
        """  wait until device is exported and server is running

        :param server: server name, check if running when not None
        :type server: :obj:`str`
        :param device: device name, check if exported when not None
        :type device: :obj:`str`
        :param adminproxy: Starter device proxy
        :type adminproxy: :obj:`tango.DeviceProxy`
        :param maxcnt: maximal waiting time in 10ms
        :type maxcnt: :obj:`int`
        :param verbose: verbose mode
        :type verbose: :obj:`bool`
        :param waitforproc: wait for process list update
        :type waitforporc: :obj:`bool`
        :returns: True if server is running
        :rtype: :obj:`bool`
        """
        found = False
        cnt = 0
        exported = False
        while not found and cnt < maxcnt:
            try:
                if device and not exported:
                    if verbose:
                        sys.stdout.write(".")
                        sys.stdout.flush()
                    exl = self.db.get_device_exported(device)
                    if device not in exl.value_string:
                        time.sleep(0.02)
                        cnt += 1
                        continue
                    else:
                        exported = True
                if server is not None and adminproxy is not None:
                    if verbose:
                        sys.stdout.write(".")
                        sys.stdout.flush()
                    adminproxy.UpdateServersInfo()
                    # running = adminproxy.RunningServers
                    running = adminproxy.DevGetRunningServers(True)
                    if server not in running:
                        time.sleep(0.02)
                        cnt += 1
                        continue
                found = True
                if verbose:
                    if device or server:
                        print(" %s is working" % (device or server))
            except Exception as e:
                print(str(e))
                time.sleep(0.02)
                found = False
            cnt += 1
        if waitforproc:
            time.sleep(1.5)
        return found

    def killServer(self, server):
        sserver = server.split("/")
        if len(sserver) > 1:
            sname = sserver[0]
            instance = sserver[1]
        if sys.version_info > (3,):
            with subprocess.Popen(
                    "ps -ef | grep '%s %s' | grep -v grep"
                    % (sname, instance),
                    stdout=subprocess.PIPE, shell=True) as proc:

                pipe = proc.stdout
                res = str(pipe.read(), "utf-8").split("\n")
                for r in res:
                    sr = r.split()
                    if len(sr) > 2:
                        subprocess.call(
                            "kill -9 %s" % sr[1], stderr=subprocess.PIPE,
                            shell=True)
                pipe.close()
        else:
            pipe = subprocess.Popen(
                "ps -ef | grep '%s %s' | grep -v grep"
                % (sname, instance),
                stdout=subprocess.PIPE, shell=True).stdout

            res = str(pipe.read()).split("\n")
            for r in res:
                sr = r.split()
                if len(sr) > 2:
                    subprocess.call(
                        "kill -9 %s" % sr[1], stderr=subprocess.PIPE,
                        shell=True)
            pipe.close()

    def restartServer(self, name, host=None, level=None,
                      restart=True, stopstart=True, wait=True,
                      timeout=None):
        """ restarts server

        :param name: server name
        :type name: :obj:`str`
        :param host: server host name
        :type host: :obj:`str`
        :param level: start up level
        :type level: :obj:`int`
        :param restart:  if server should be restarted
        :type restart: :obj:`bool`
        :param stopstart:  if server should be stopped and started
        :type stopstart: :obj:`bool`
        :param wait:  script should wait for the server
        :type wait: :obj:`bool`
        :param timeout: timeout for  start
        :type timeout: :obj:`float`
        """
        if name:
            admin = self.getStarterName(host)
            if not admin:
                raise Exception("Starter tango server is not running")
            if admin:
                servers = None
                started = None
                try:
                    adminproxy = tango.DeviceProxy(admin)
                    adminproxy.UpdateServersInfo()
                    servers = self.__registered_servers()
                    started = adminproxy.DevGetRunningServers(True)
                except Exception:
                    pass
                if servers:
                    for vl in set(servers):
                        svl = vl.split('\t')[0]
                        if name.startswith("NXSRecSelector") \
                                and svl.startswith("NXSRecSelector"):
                            self._changeLevel(svl, 4)
                        if (started and svl in started) or not restart:
                            if '/' in name:
                                cname = svl
                            else:
                                cname = svl.split('/')[0]
                            if cname == name:
                                if level is not None:
                                    self._changeLevel(
                                        svl, level, tohigher=False)
                                problems = False
                                if stopstart:
                                    if started and svl in started:
                                        try:
                                            # adminproxy.HardKillServer(svl)
                                            adminproxy.DevStop(svl)
                                            # self.killServer(svl)
                                        except Exception:
                                            adminproxy.HardKillServer(svl)
                                        problems = self.waitServerNotRunning(
                                            svl, None, adminproxy,
                                            verbose=None)
                                        if problems:
                                            self.killServer(svl)
                                            print("Server Running")
                                        sys.stdout.write(
                                            "Restarting: %s" % svl)
                                    else:
                                        sys.stdout.write("Starting: %s" % svl)
                                    sys.stdout.flush()
                                    problems = True
                                    counter = 0
                                    while problems and counter < 1000:
                                        try:
                                            sys.stdout.write('.')
                                            sys.stdout.flush()
                                            adminproxy.DevStart(svl)
                                            problems = False
                                        except Exception:
                                            counter += 1
                                            time.sleep(0.2)
                                if wait:
                                    try:
                                        maxcnt = int(float(timeout)/0.02)
                                    except Exception:
                                        maxcnt = 10000
                                    problems = not self.waitServerRunning(
                                        svl, None, adminproxy, maxcnt) \
                                        or problems
                                    if problems:
                                        print("%s was not restarted" % svl)
                                        print("Warning: "
                                              "Process with the server"
                                              "instance could be suspended")
                                else:
                                    print("")

    def __exported_servers(self):
        """ returns Servers for exported devices

        :rtype: :obj:`list` <:obj:`str`>
        :returns: server list
        """
        dvexported = self.db.get_device_exported("*").value_string
        return [sv for sv in self.db.get_server_list()
                if (set(self.db.get_device_class_list(sv).value_string[:2])
                    & set(dvexported))]

    def __registered_servers(self):
        """ returns registered Servers

        :rtype: :obj:`list` <:obj:`str`>
        :returns: server list
        """
        hosts = self.db.get_host_list().value_string
        svlist = []
        for ht in hosts:
            svlist.extend(self.db.get_host_server_list(ht).value_string)
        return svlist

    def stopServer(self, name, host=None):
        """ restarts server

        :param name: server name
        :type name: :obj:`str`
        :param host: server host name
        :type host: :obj:`str`
        """
        if name:
            admin = self.getStarterName(host)
            if not admin:
                raise Exception("Starter tango server is not running")
            if admin:
                servers = None
                started = None
                try:
                    adminproxy = tango.DeviceProxy(admin)
                    adminproxy.UpdateServersInfo()
                    started = adminproxy.DevGetRunningServers(True)
                    servers = self.__registered_servers()
                except Exception:
                    pass
                if servers:
                    for vl in set(servers):
                        svl = vl.split('\t')[0]
                        if started and svl in started:
                            if '/' in name:
                                cname = svl
                            else:
                                cname = svl.split('/')[0]
                            if cname == name:
                                if started and svl in started:
                                    try:
                                        adminproxy.DevStop(svl)
                                    except Exception:
                                        adminproxy.HardKillServer(svl)

                                    sys.stdout.write("Stopping: %s" % svl)
                                    sys.stdout.flush()
                                problems = self.waitServerNotRunning(
                                    svl, None, adminproxy)
                                print(" ")
                                if problems:
                                    print("%s was not stopped" % svl)
                                    print("Warning: Process with the server"
                                          "instance could be suspended")

    def _changeLevel(self, name, level, tohigher=True):
        """ change startup level

        :param name: server name
        :type name: :obj:`str`
        :param level: new startup level
        :type level: :obj:`int`
        :returns: True if level was changed
        :rtype: :obj:`bool`
        """
        sinfo = self.db.get_server_info(name)
        if not tohigher or level > sinfo.level:
            sinfo.level = level
        self.db.put_server_info(sinfo)
        return True

    def _startupServer(self, new, level, host, ctrl, device, postpone=False):
        """ starts the server up

        :param new: new server name
        :type new: :obj:`str`
        :param level: startup level
        :type level: :obj:`int`
        :param host: tango host name
        :type host: :obj:`str`
        :param ctrl: control mode
        :type ctrl: :obj:`str`
        :param device: device name
        :type device: :obj:`str`
        :param postpone: postpone start server
        :type postpone: :obj:`bool`
        :returns: True if server was started up
        :rtype: :obj:`bool`
        """
        print("S1", new, level, host, ctrl, device, postpone)
        server = self.db.get_server_class_list(new)
        print("S2", server)
        if len(server) == 0:
            sys.stderr.write('Server ' + new.split('/')[0]
                             + ' not defined in database\n')
            sys.stderr.flush()
            return False
        print("S3", host)
        admin = self.getStarterName(host)
        if not admin:
            raise Exception("Starter tango server is not running")
        print("S4", admin)
        adminproxy = tango.DeviceProxy(admin)
        startdspaths = self.db.get_device_property(
            admin,
            "StartDsPath")["StartDsPath"]
        print("S5", startdspaths)
        if '/usr/bin' not in startdspaths:
            print("S6", startdspaths)
            
            if startdspaths:
                startdspaths = [p for p in startdspaths if p]
            else:
                startdspaths = []
            startdspaths.append('/usr/bin')
            self.db.put_device_property(
                admin, {"StartDsPath": startdspaths})
            adminproxy.Init()
        print("S7",startdspaths, new)

        try:
            sinfo = self.db.get_server_info(new)
        except Exception as e:
            print(str(e))
            sinfo = tango.DbServerInfo()
            
        print("S7a",sinfo, new, host, ctrl, level)
        sinfo.name = new
        sinfo.host = host
        sinfo.mode = ctrl
        sinfo.level = level
        self.db.put_server_info(sinfo)
        print("S8",sinfo)
        adminproxy.UpdateServersInfo()
        running = adminproxy.DevGetRunningServers(True)
        print("S9",running)
        # running = adminproxy.RunningServers
        if new not in running and not postpone:
            print("S10",new)
            adminproxy.DevStart(new)
        else:
            print("S11",new)
            print("%s NOT STARTED" % new)

        adminproxy.UpdateServersInfo()
        print("S12")

        if not postpone:
            print("S13")
            sys.stdout.write("waiting for server ")
            sys.stdout.flush()
            return self.waitServerRunning(new, device, adminproxy)
        print("S14")

    def createDataWriter(self, beamline, masterhost, postpone=False):
        """ creates data writer

        :param beamline: beamline name
        :type beamline: :obj:`str`
        :param masterhost: master host of data writer
        :type masterhost: :obj:`str`
        :param postpone: postpone starting flag
        :type postpone: :obj:`bool`
        :returns: True if server was created
        :rtype: :obj:`bool`
        """
        if not beamline:
            print("createDataWriter: no beamline given ")
            return False
        if not masterhost:
            print("createDataWriter: no masterhost given ")
            return False

        class_name = 'NXSDataWriter'
        server = class_name
        server_name = server + '/' + masterhost
        full_class_name = 'NXSDataWriter/' + masterhost
        self.writer_name = "%s/nxsdatawriter/%s" % (beamline, masterhost)
        if server_name not in self.db.get_server_list(server_name):
            print("creating: %s" % server_name)

            if server_name in self.db.get_server_list(server_name):
                print("createDataWriter: DB contains already %s" % server_name)
                return False

            di = tango.DbDevInfo()
            di.name = self.writer_name
            di._class = class_name
            di.server = server_name

            self.db.add_device(di)
            self.db.put_device_property(self.writer_name,
                                        {'NumberOfThreads': 100})

        elif (self.writer_name not in
              self.db.get_device_class_list(server_name).value_string):
            print("\ncreateDataWriter: %s already exists. "
                  "To change its device name please remove it." % server_name)
            return False

        hostname = socket.gethostname()

        self._startupServer(full_class_name, 1, hostname, 1, self.writer_name,
                            postpone)

        return True

    def createServer(self, server_name, beamline, masterhost, hostname=None,
                     class_name=None, jsondeviceproperties=None,
                     postpone=False):
        """ creates tango server in DB

        :param server_name: server name
        :type server_name: :obj:`str`
        :param beamline: beamline name
        :type beamline: :obj:`str`
        :param masterhost: master host of data writer
        :type masterhost: :obj:`str`
        :param hostname: host to run the config server
        :type hostname: :obj:`str`
        :param class_name: class name
        :type clas_name: :obj:`str`
        :param jsondeviceproperties: json device properties
        :type jsondeviceproperties: :obj:`str`
        :param postpone: postpone starting flag
        :type postpone: :obj:`bool`
        :returns: True if server was created
        :rtype: :obj:`bool`
        """
        if not beamline:
            print("createServer: no beamline given ")
            return False
        if not masterhost:
            print("createServer: no masterhost given ")
            return False

        if "/" not in server_name:
            server_name = server_name + '/' + masterhost
        server = server_name.split("/")[0]
        if not class_name:
            class_name = server
        self.device_name = "%s/%s/%s" % (beamline, server.lower(), masterhost)
        if server_name not in self.db.get_server_list(server_name):
            print("creating: %s" % server_name)

            if server_name in self.db.get_server_list(server_name):
                print("createDataWriter: DB contains already %s" % server_name)
                return False

            try:
                properties = dict(json.loads(jsondeviceproperties))
            except Exception:
                print("\ncreateServer: properties cannot be load")
                properties = {}
            if not properties:
                properties = {self.device_name: {}}

            print("PROP", properties)
            for dv, props in properties.items():
                di = tango.DbDevInfo()
                di.name = dv
                di._class = class_name
                di.server = server_name
                self.db.add_device(di)
                try:
                    self.db.put_device_property(dv, props)
                except Exception:
                    print("\ncreateServer: properties cannot be added")

        elif (self.device_name not in
              self.db.get_device_class_list(server_name).value_string):
            print("\ncreateServer: %s already exists. "
                  "To change its device name please remove it." % server_name)
            return False

        if not hostname:
            hostname = socket.gethostname()

        self._startupServer(server_name, 1, hostname, 1, self.device_name,
                            postpone)

        return True

    def createConfigServer(self, beamline, masterhost, jsonsettings=None,
                           hostname=None, postpone=False):
        """ creates configuration server

        :param beamline: beamline name
        :type beamline: :obj:`str`
        :param masterhost: master host of data writer
        :type masterhost: :obj:`str`
        :param jsonsettings: connection settings to DB in json
        :type jsonsettings: :obj:`str`
        :param hostname: host to run the config server
        :type hostname: :obj:`str`
        :param postpone: postpone starting flag
        :type postpone: :obj:`bool`
        :returns: True if server was created
        :rtype: :obj:`bool`
        """
        print("C1")
        if not beamline:
            print("createConfigServer: no beamline given ")
            return False
        if not masterhost:
            print("createConfigServer: no masterhost given ")
            return False

        class_name = 'NXSConfigServer'
        server = class_name
        server_name = server + '/' + masterhost
        self.cserver_name = "%s/nxsconfigserver/%s" % (beamline, masterhost)
        print("C2")
        if server_name not in self.db.get_server_list(server_name):
            print("creating: %s" % server_name)

            if server_name in self.db.get_server_list(server_name):
                print("createConfigServer: DB contains already %s"
                      % server_name)
                return False

            di = tango.DbDevInfo()
            di.name = self.cserver_name
            di._class = class_name
            di.server = server_name

            self.db.add_device(di)
            self.db.put_device_property(
                self.cserver_name, {'VersionLabel': '%s@%s' % (
                    beamline.upper(), masterhost.upper())})
        elif (self.cserver_name not in
              self.db.get_device_class_list(server_name).value_string):
            print("\ncreateConfigServer: %s already exists. "
                  "To change its device name please remove it." % server_name)
            return False

        print("C3")
        if not hostname:
            hostname = self.db.get_db_host().split(".")[0]

        print("C3a")
        self._startupServer(server_name, 1, hostname, 1, self.cserver_name,
                            postpone)

        print("C4")
        if not postpone:
            dp = tango.DeviceProxy(self.cserver_name)
            if dp.state() != tango.DevState.ON:
                dp.Close()
            if jsonsettings:
                dp = tango.DeviceProxy(self.cserver_name)
                dp.JSONSettings = jsonsettings
            try:
                dp.Open()
            except Exception:
                try:
                    jsettings = json.loads(jsonsettings)
                    jsettings['read_default_file'] = \
                        '/var/lib/nxsconfigserver/.my.cnf'
                    dp.JSONSettings = str(json.dumps(jsettings))
                    dp.Open()
                except Exception:
                    try:
                        jsettings['read_default_file'] = \
                            '/var/lib/nxsconfigserver/.my.cnf'
                        dp.JSONSettings = str(json.dumps(jsettings))
                        dp.Open()
                    except Exception:
                        print("createConfigServer: "
                              "%s cannot connect the"
                              " database with JSONSettings: \n%s " % (
                                  self.cserver_name, jsonsettings))
                        print("try to change the settings")
                        return False

        print("C5")
        return True

    def createSelector(self, beamline, masterhost, writer=None, cserver=None,
                       postpone=False):
        """ creates selector server

        :param beamline: beamline name
        :type beamline: :obj:`str`
        :param masterhost: master host of data writer
        :type masterhost: :obj:`str`
        :param writer: writer device name
        :type writer: :obj:`str`
        :param cserver: configuration server device name
        :type cserver: :obj:`str`
        :param postpone: postpone starting flag
        :type postpone: :obj:`bool`
        :returns: True if server was created
        :rtype: :obj:`bool`
        """
        if not beamline:
            print("createSelector: no beamline given ")
            return False
        if not masterhost:
            print("createSelector: no masterhost given ")
            return False
        if writer:
            self.writer_name = writer
        if cserver:
            self.cserver_name = cserver

        class_name = 'NXSRecSelector'
        server = class_name
        server_name = server + '/' + masterhost
        full_class_name = 'NXSRecSelector/' + masterhost
        device_name = "%s/nxsrecselector/%s" % (beamline, masterhost)
        if server_name not in self.db.get_server_list(server_name):
            print("creating: %s" % server_name)

            if server_name in self.db.get_server_list(server_name):
                print("createSelector: DB contains already %s" % server_name)
                return False

            di = tango.DbDevInfo()
            di.name = device_name
            di._class = class_name
            di.server = server_name
            self.db.add_device(di)

        elif (device_name not in
              self.db.get_device_class_list(server_name).value_string):
            print("\ncreateSelector: %s already exists. "
                  "To change its device name please remove it." % server_name)
            return False

        hostname = socket.gethostname()

        self._startupServer(full_class_name, 4, hostname, 1,
                            device_name, postpone)

        if not postpone:
            if self.writer_name or self.cserver_name:
                dp = tango.DeviceProxy(device_name)
                dp.ping()
                self.waitServerRunning(None, device_name)
                if self.cserver_name:
                    dp.configDevice = self.cserver_name
                if self.writer_name:
                    dp.writerDevice = self.writer_name
        return True


class Set(Runner):

    """ set runner"""

    #: (:obj:`str`) command description
    description = "set up NXSConfigServer NXSDataWriter " \
                  + "and NXSRecSelector servers"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsetup set\n" \
        + "       nxsetup set -b p09 -m haso228 -u p09user " \
        + "-d nxsconfig NXSConfigServer\n" \
        + "       nxsetup set NexusWriter/haso228  -k NexusWriter  " \
        + "-y '{\"p00/bliss_nexuswriter/test_session\":" \
        + "{\"session\":\"test_session\"," \
        + "\"beacon_host\":\"haso228:25000\"}}'  -t\n" \
        + "\n"

    def create(self):
        """ creates parser
        """
        parser = self._parser
        parser.add_argument(
            "-b", "--beamline", action="store",
            dest="beamline", help="name of the beamline"
            " ( default: 'nxs' )")
        parser.add_argument(
            "-m", "--masterhost", action="store",
            dest="masterhost", help="the host that stores the Mg"
            " ( default: <localhost> )")
        parser.add_argument(
            "-c", "--confighost", action="store",
            dest="confighost", help="the host run the config server"
            " ( default: <mysqlhost> )")
        parser.add_argument(
            "-r", "--runhost", action="store",
            dest="runhost", help="the host to run the server"
            " ( default: localhost )")
        parser.add_argument(
            "-u", "--user", action="store",
            dest="user", help="the local user"
            " ( default: 'tango' )")
        parser.add_argument(
            "-d", "--database", action="store",
            dest="dbname", help="the database name"
            "  ( default: 'nxsconfig')")
        parser.add_argument(
            "-j", "--csjson", action="store",
            dest="csjson",
            help="JSONSettings for the configuration server. "
            "( default: '{\"host\": \"localhost\",\"db\": <DBNAME>,"
            " \"use_unicode\": true,"
            " \"read_default_file\": <MY_CNF_FILE>}'"
            "  where <MY_CNF_FILE> stays for"
            " \"/home/<USER>/.my.cnf\""
            " or \"/var/lib/nxsconfigserver/.my.cnf\" )")
        parser.add_argument(
            "-k", "--class-name", action="store",
            dest="classname", help="tango server class name")
        parser.add_argument(
            "-y", "--json-device-properties", action="store",
            dest="propjson",
            help="JSON tango device properties "
            "( default: '{}' )")
        parser.add_argument(
            "-t", "--postpone", action="store_true",
            default=False, dest="postpone",
            help="do not start the server")
        parser.add_argument(
            'args', metavar='server_name',
            type=str, nargs='*',
            help='server names, e.g.: NXSRecSelector NXSConfigServer')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        local_user = None
        args = options.args or []
        if os.path.isfile('/home/etc/local_user'):
            with open('/home/etc/local_user') as fl:
                local_user = fl.readline()
        elif _hostname in knownHosts.keys():
            local_user = knownHosts["user"]

        if options.beamline is None:
            if _hostname in knownHosts.keys():
                options.beamline = knownHosts[_hostname]['beamline']
            else:
                options.beamline = 'nxs'

        if options.masterhost is None:
            if _hostname in knownHosts.keys():
                options.masterhost = knownHosts[_hostname]['masterhost']
            else:
                options.masterhost = _hostname

        if options.user is None:
            if local_user:
                options.user = local_user
            else:
                options.user = 'tango'

        if options.dbname is None:
            if _hostname in knownHosts.keys():
                options.dbname = knownHosts[_hostname]['dbname']
            else:
                options.dbname = 'nxsconfig'

        print("\noptions are set to:  -b %s -m %s -u %s -d %s \n" % (
            options.beamline,
            options.masterhost,
            options.user,
            options.dbname,
        ))

        setUp = SetUp()

        if not args or "NXSDataWriter" in args:
            if not setUp.createDataWriter(
                    beamline=options.beamline,
                    masterhost=options.masterhost):
                print("startup failed to create the nexus data writer")
                sys.exit(255)

        if options.csjson:
            jsonsettings = options.csjson
        else:
            jsonsettings = '{"db":"%s",' % options.dbname \
                + ' "read_default_file":"/home/%s/.my.cnf",' % options.user \
                + ' "use_unicode":true}'

        if options.propjson:
            jsondeviceproperties = options.propjson
        else:
            jsondeviceproperties = '{}'

        if not args or "NXSConfigServer" in args:
            if not setUp.createConfigServer(
                    beamline=options.beamline,
                    masterhost=options.masterhost,
                    jsonsettings=jsonsettings,
                    hostname=options.confighost,
                    postpone=options.postpone):
                print("startup failed to create the nexus config server")
                sys.exit(255)

        if not args or "NXSRecSelector" in args:
            if not setUp.createSelector(
                    beamline=options.beamline,
                    masterhost=options.masterhost,
                    postpone=options.postpone):
                print("startup failed to create the nexus selector server")
                sys.exit(255)
        for arg in args:
            if arg not in ["NXSDataWriter", "NXSRecSelector",
                           "NXSConfigServer"]:
                if not setUp.createServer(
                        arg,
                        beamline=options.beamline,
                        masterhost=options.masterhost,
                        hostname=options.runhost,
                        class_name=options.classname,
                        jsondeviceproperties=jsondeviceproperties,
                        postpone=options.postpone):
                    print("startup failed to create the %s server" % arg)
                    sys.exit(255)


class Start(Runner):

    """ start runner"""

    #: (:obj:`str`) command description
    description = "start tango server"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsetup start Pool/haso228 -l 2\n" \
        + "\n"

    def create(self):
        """ creates parser
        """
        parser = self._parser
        parser.add_argument(
            "-l", "--level", action="store", type=int, default=-1,
            dest="level", help="startup level")
        parser.add_argument(
            "-z", "--timeout", action="store", type=float, default=None,
            dest="timeout", help="timeout in seconds")
        parser.add_argument(
            "-e", "--no-wait", action="store_true",
            default=False, dest="nowait",
            help="do not wait")
        parser.add_argument(
            'args', metavar='server_name',
            type=str, nargs='*',
            help='server names, e.g.: NXSRecSelector NXSDataWriter/TDW1')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        args = options.args or []
        setUp = SetUp()
        servers = args if args else [
            "NXSConfigServer", "NXSRecSelector", "NXSDataWriter"]
        for server in servers:
            setUp.restartServer(
                server,
                level=(options.level if options.level > -1 else None),
                restart=False, timeout=options.timeout,
                wait=(not options.nowait))


class Wait(Runner):

    """ start runner"""

    #: (:obj:`str`) command description
    description = "wait for tango server"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsetup wait Pool/haso228 -z 30\n" \
        + "\n"

    def create(self):
        """ creates parser
        """
        parser = self._parser
        parser.add_argument(
            "-z", "--timeout", action="store", type=float, default=None,
            dest="timeout", help="timeout in seconds")
        parser.add_argument(
            'args', metavar='server_name',
            type=str, nargs='*',
            help='server names, e.g.: NXSRecSelector NXSDataWriter/TDW1')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        args = options.args or []
        setUp = SetUp()
        servers = args if args else [
            "NXSConfigServer", "NXSRecSelector", "NXSDataWriter"]
        for server in servers:
            setUp.restartServer(
                server,
                restart=False, stopstart=False, timeout=options.timeout)


class MoveProp(Runner):

    """ move-prop runner"""

    #: (:obj:`str`) command description
    description = "change property name"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsetup move-prop -n DefaultPreselectedComponents" \
        + " -o DefaultAutomaticComponents NXSRecSelector\n" \
        + "       nxsetup move-prop -t -n DefaultPreselectedComponents " \
        + " -o DefaultAutomaticComponents NXSRecSelector\n" \
        + "\n"

    def create(self):
        """ creates parser
        """
        parser = self._parser
        parser.add_argument(
            "-n", "--newname", action="store",
            dest="newname", help="(new) property name")
        parser.add_argument(
            "-o", "--oldname", action="store",
            dest="oldname", help="old property name")
        parser.add_argument(
            "-t", "--postpone", action="store_true",
            default=False, dest="postpone",
            help="do not restart the server")
        parser.add_argument(
            "-z", "--timeout", action="store", type=float, default=None,
            dest="timeout", help="timeout in seconds")
        parser.add_argument(
            "-e", "--no-wait", action="store_true",
            default=False, dest="nowait",
            help="do not wait")
        parser.add_argument(
            'args', metavar='server_name',
            type=str, nargs='*',
            help='server names, e.g.: NXSRecSelector NXSDataWriter/TDW1')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        parser = self._parser
        args = options.args or []
        if not options.newname or not options.oldname or not args:
            parser.print_help()
            sys.exit(255)
        servers = args or []
        setUp = SetUp()
        for server in servers:
            if setUp.changePropertyName(
                    server, options.oldname, options.newname):
                if not options.postpone:
                    setUp.restartServer(
                        server, timeout=options.timeout,
                        wait=(not options.nowait))


class ChangeProp(Runner):

    """ change-prop runner"""

    #: (:obj:`str`) command description
    description = "change property value"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsetup change-prop -n ClientRecordKeys -t -w " \
        + "\"[\\\"phoibos_scan_command\\\",\\\"phoibos_scan_comment\\\"]\" " \
        + "NXSRecSelector/r228\n" \
        + "       nxsetup change-prop -n DefaultPreselectedComponents -w " \
        + "\"[\\\"pinhole1\\\",\\\"slit2\\\"]\" NXSRecSelector/r228\n" \
        + "       nxsetup change-prop -n StartDsPath -w " \
        + "\"[\\\"/usr/bin\\\",\\\"/usr/lib/tango\\\"]\" Starter\n" \
        + "\n"

    def create(self):
        """ creates parser
        """
        parser = self._parser
        parser.add_argument(
            "-n", "--newname", action="store",
            dest="newname", help="(new) property name")
        parser.add_argument(
            "-w", "--propvalue", action="store",
            dest="propvalue", help="new property value")
        parser.add_argument(
            "-t", "--postpone", action="store_true",
            default=False, dest="postpone",
            help="do not restart the server")
        parser.add_argument(
            "-z", "--timeout", action="store", type=float, default=None,
            dest="timeout", help="timeout in seconds")
        parser.add_argument(
            "-e", "--no-wait", action="store_true",
            default=False, dest="nowait",
            help="do not wait")
        parser.add_argument(
            'args', metavar='server_name',
            type=str, nargs='*',
            help='server names, e.g.: NXSRecSelector NXSDataWriter/TDW1')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        parser = self._parser
        args = options.args or []
        if not options.newname or not options.propvalue or not args:
            parser.print_help()
            sys.exit(255)
        servers = args or []
        setUp = SetUp()
        for server in servers:
            if setUp.changePropertyValue(
                    server, options.newname, options.propvalue):
                if not options.postpone:
                    setUp.restartServer(
                        server,
                        timeout=options.timeout, wait=(not options.nowait))


class AddRecorderPath(Runner):

    """ add-recorder-path runner"""

    #: (:obj:`str`) command description
    description = "add-recorder-path into MacroServer(s) property"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsetup add-recorder-path "\
        + "/usr/share/pyshared/sardananxsrecorder\n" \
        + "       nxsetup add-recorder-path -t "\
        + "/usr/share/pyshared/sardananxsrecorder\n" \
        + "       nxsetup add-recorder-path "\
        + "/usr/share/pyshared/sardananxsrecorder -i haso\n" \
        + "\n"

    def create(self):
        """ creates parser
        """
        parser = self._parser
        parser.add_argument(
            "-t", "--postpone", action="store_true",
            default=False, dest="postpone",
            help="do not restart the server")
        parser.add_argument(
            "-z", "--timeout", action="store", type=float, default=None,
            dest="timeout", help="timeout in seconds")
        parser.add_argument(
            "-e", "--no-wait", action="store_true",
            default=False, dest="nowait",
            help="do not wait")
        parser.add_argument(
            "-i", "--instance", action="store",
            dest="instance",
            help="macroserver instance name, i.e. haso"
            " ( default: '*')")

    def postauto(self):
        """ creates parser
        """
        parser = self._parser
        parser.add_argument(
            'recpath', metavar='recorder_path',
            type=str, nargs=1,
            help='sardana recorder path')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        if options.instance is None:
            options.instance = "*"

        setUp = SetUp()
        if setUp.changeRecorderPath(
                options.recpath[0], options.instance):
            if not options.postpone:
                if options.instance != "*":
                    ms = "MacroServer/%s" % options.instance
                else:
                    ms = "MacroServer"
                setUp.restartServer(ms, timeout=options.timeout,
                                    wait=(not options.nowait))


class Restart(Runner):

    """ restart runner"""

    #: (:obj:`str`) command description
    description = "restart tango server"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsetup restart Pool/haso228 -l 2\n" \
        + "\n"

    def create(self):
        """ creates parser
        """
        parser = self._parser
        parser.add_argument(
            "-l", "--level", action="store", type=int, default=-1,
            dest="level", help="startup level")
        parser.add_argument(
            "-z", "--timeout", action="store", type=float, default=None,
            dest="timeout", help="timeout in seconds")
        parser.add_argument(
            "-e", "--no-wait", action="store_true",
            default=False, dest="nowait",
            help="do not wait")
        parser.add_argument(
            'args', metavar='server_name',
            type=str, nargs='*',
            help='server names, e.g.: NXSRecSelector NXSDataWriter/TDW1')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        args = options.args or []
        setUp = SetUp()
        servers = args if args else [
            "NXSConfigServer", "NXSRecSelector", "NXSDataWriter"]
        for server in servers:
            setUp.restartServer(
                server, level=(options.level if options.level > -1 else None),
                timeout=options.timeout, wait=(not options.nowait))


class Stop(Runner):

    """ Stop runner"""

    #: (:obj:`str`) command description
    description = "stop tango server"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsetup stop Pool/haso228 \n" \
        + "\n"

    def create(self):
        """ creates parser
        """
        parser = self._parser
        parser.add_argument(
            'args', metavar='server_name',
            type=str, nargs='*',
            help='server names, e.g.: NXSRecSelector NXSDataWriter/TDW1')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        args = options.args or []
        setUp = SetUp()
        servers = args if args else [
            "NXSConfigServer", "NXSRecSelector", "NXSDataWriter"]
        for server in servers:
            setUp.stopServer(server)


def _supportoldcommands():
    """ replace the old command names to the new ones
    """

    oldnew = {
        '-x': 'set',
        '--execute': 'set',
        '-r': 'restart',
        '--restart': 'restart',
        '-s': 'start',
        '--start': 'start',
        '-p': 'move-prop',
        '--move-prop': 'move-prop',
        '-c': 'change-prop',
        '--change-prop': 'change-prop',
        '-a': 'add-recorder-path',
        '--add-recorder-path': 'add-recorder-path',
    }

    if sys.argv and len(sys.argv) > 1:
        if sys.argv[1] in oldnew.keys():
            sys.argv[1] = oldnew[sys.argv[1]]


def main():
    """ the main program function
    """
    description = "Command-line tool for setting up  NeXus Tango Servers"

    _supportoldcommands()

    epilog = 'For more help:\n  nxsetup <sub-command> -h'
    if _hostname in knownHosts.keys():
        local_user = None
        if os.path.isfile('/home/etc/local_user'):
            with open('/home/etc/local_user') as fl:
                local_user = fl.readline()
        elif _hostname in knownHosts.keys():
            local_user = knownHosts["user"]
        epilog += "\n\n  (%s is known: -b %s -m %s -u %s -d %s )" % (
            _hostname,
            knownHosts[_hostname]['beamline'],
            knownHosts[_hostname]['masterhost'],
            local_user,
            knownHosts[_hostname]['dbname']
        )

    parser = NXSArgParser(
        description=description, epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.cmdrunners = [
        ('set', Set),
        ('restart', Restart),
        ('start', Start),
        ('stop', Stop),
        ('wait', Wait),
        ('move-prop', MoveProp),
        ('change-prop', ChangeProp),
        ('add-recorder-path', AddRecorderPath),
    ]
    runners = parser.createSubParsers()

    try:
        options = parser.parse_args()
    except ErrorException as e:
        sys.stderr.write("Error: %s\n" % str(e))
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

    runners[options.subparser].run(options)


if __name__ == "__main__":
    main()
