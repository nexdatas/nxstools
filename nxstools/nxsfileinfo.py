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

""" Command-line tool for showing meta data from Nexus Files"""

import sys
import argparse
import json
import uuid
import os
import stat
import re
import time
import datetime
import pwd
import grp
import fnmatch
import yaml
import base64
import math
import shutil
import numpy as np
from io import BytesIO

from .nxsparser import TableTools
from .nxsfileparser import (NXSFileParser, FIOFileParser,
                            numpyEncoder, numpyEncoderNull, isoDate)
from .nxsargparser import (Runner, NXSArgParser, ErrorException)
from . import filewriter
from .ontology import id_techniques, nexus_panet


if sys.version_info > (3,):
    basestring = str


WRITERS = {}
try:
    from . import h5pywriter
    WRITERS["h5py"] = h5pywriter
except Exception:
    pass

try:
    from . import h5cppwriter
    WRITERS["h5cpp"] = h5cppwriter
except Exception:
    pass

try:
    import matplotlib
    MATPLOTLIB = True
except Exception:
    MATPLOTLIB = False

# try:
#     import PIL
#     import PIL.Image
#     #: (:obj:`bool`) PIL imported
#     PILLOW = True
# except ImportError:
#     #: (:obj:`bool`) PIL imported
#     PILLOW = False


def getlist(text):
    """ converts a text string to a list of lists
        with respect to newline and space characters

    :param text: parser options
    :type text: :obj:`str`
    :returns: a list of list
    :rtype: :obj:`list` < :obj:`list`<:obj:`str`> >
    """
    lst = []
    if text:
        lines = text.strip().split("\n")
        lst = [line.strip().split(" ") for line in lines
               if (line.strip() and not line.strip().startswith("#"))]
    return lst


def splittext(text, lmax=68):
    """ split text to lines

    :param text: parser options
    :type text: :obj:`str`
    :param lmax: maximal line length
    :type lmax: :obj:`int`
    :returns: split text
    :rtype: :obj:`str`
    """
    lnew = []

    lw = [" " + ee for ee in text.split(" ") if ee]
    nw = []
    for ew in lw:
        ww = [ee + "," for ee in ew.split(",") if ee]
        ww[-1] = ww[-1][:-1]
        nw.extend(ww)

    for ll in nw:
        if ll:
            if not lnew and ll[1:]:
                lnew.append(ll[1:])
            elif len(lnew[-1]) + len(ll) < lmax:
                lnew[-1] = lnew[-1] + ll
            else:
                lnew.append(ll)
    return "\n".join(lnew)


class General(Runner):

    """ General runner"""

    #: (:obj:`str`) command description
    description = "show general information for the nexus file"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsfileinfo general /user/data/myfile.nxs\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        self._parser.add_argument(
            "--h5py", action="store_true",
            default=False, dest="h5py",
            help="use h5py module as a nexus reader")
        self._parser.add_argument(
            "--h5cpp", action="store_true",
            default=False, dest="h5cpp",
            help="use h5cpp module as a nexus reader")

    def postauto(self):
        """ parser creator after autocomplete run """
        self._parser.add_argument(
            'args', metavar='nexus_file', type=str, nargs=1,
            help='new nexus file name')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        if options.h5cpp:
            writer = "h5cpp"
        elif options.h5py:
            writer = "h5py"
        elif "h5cpp" in WRITERS.keys():
            writer = "h5cpp"
        else:
            writer = "h5py"
        if (options.h5py and options.h5cpp) or \
           writer not in WRITERS.keys():
            sys.stderr.write("nxsfileinfo: Writer '%s' cannot be opened\n"
                             % writer)
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)
        wrmodule = WRITERS[writer.lower()]
        try:
            fl = filewriter.open_file(
                options.args[0], readonly=True,
                writer=wrmodule)
        except Exception:
            sys.stderr.write("nxsfileinfo: File '%s' cannot be opened\n"
                             % options.args[0])
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)

        root = fl.root()
        self.show(root)
        fl.close()

    @classmethod
    def parseentry(cls, entry, description):
        """ parse entry of nexus file

        :param entry: nexus entry node
        :type entry: :class:`filewriter.FTGroup`
        :param description: dict description list
        :type description: :obj:`list` <:obj:`dict` <:obj:`str`, `any` > >
        :return: (key, value) name pair of table headers
        :rtype: [:obj:`str`, :obj:`str`]

        """
        key = "A"
        value = "B"
        at = None
        try:
            at = entry.attributes["NX_class"]
        except Exception:
            pass
        if at and filewriter.first(at.read()) == 'NXentry':
            # description.append(None)
            # value = filewriter.first(value)
            key = "Scan entry:"
            value = entry.name
            # description.append({key: "Scan entry:", value: entry.name})
            # description.append(None)
            try:
                vl = filewriter.first(entry.open("title").read())
                description.append(
                    {key: "Title:", value: vl})
            except Exception:
                sys.stderr.write("nxsfileinfo: title cannot be found\n")
                sys.stderr.flush()
            try:
                vl = filewriter.first(
                    entry.open("experiment_identifier").read())
                description.append(
                    {key: "Experiment identifier:",
                     value: vl})
            except Exception:
                sys.stderr.write(
                    "nxsfileinfo: experiment identifier cannot be found\n")
                sys.stderr.flush()
            for ins in entry:
                if isinstance(ins, filewriter.FTGroup):
                    iat = ins.attributes["NX_class"]
                    if iat and filewriter.first(iat.read()) == 'NXinstrument':
                        try:
                            vl = filewriter.first(ins.open("name").read())
                            description.append({
                                key: "Instrument name:",
                                value: vl})
                        except Exception:
                            sys.stderr.write(
                                "nxsfileinfo: instrument name cannot "
                                "be found\n")
                            sys.stderr.flush()
                        try:
                            vl = filewriter.first(
                                ins.open("name").attributes[
                                    "short_name"].read())
                            description.append({
                                key: "Instrument short name:",
                                value: vl
                            })
                        except Exception:
                            sys.stderr.write(
                                "nxsfileinfo: instrument short name cannot"
                                " be found\n")
                            sys.stderr.flush()

                        for sr in ins:
                            if isinstance(sr, filewriter.FTGroup):
                                sat = sr.attributes["NX_class"]
                                if sat and filewriter.first(sat.read()) \
                                   == 'NXsource':
                                    if "name" not in sr.names():
                                        continue
                                    try:
                                        vl = filewriter.first(
                                            sr.open("name").read())
                                        description.append({
                                            key: "Source name:",
                                            value: vl})
                                    except Exception:
                                        sys.stderr.write(
                                            "nxsfileinfo: source name"
                                            " cannot be found\n")
                                        sys.stderr.flush()
                                    try:
                                        vl = filewriter.first(
                                            sr.open("name").attributes[
                                                "short_name"].read())
                                        description.append({
                                            key: "Source short name:",
                                            value: vl})
                                    except Exception:
                                        sys.stderr.write(
                                            "nxsfileinfo: source short name"
                                            " cannot be found\n")
                                        sys.stderr.flush()
                    elif iat and filewriter.first(iat.read()) == 'NXsample':
                        try:
                            vl = filewriter.first(ins.open("name").read())
                            description.append({
                                key: "Sample name:",
                                value: vl})
                        except Exception:
                            sys.stderr.write(
                                "nxsfileinfo: sample name cannot be found\n")
                            sys.stderr.flush()
                        try:
                            vl = filewriter.first(
                                ins.open("chemical_formula").read())
                            description.append({
                                key: "Sample formula:",
                                value: vl})
                        except Exception:
                            sys.stderr.write(
                                "nxsfileinfo: sample formula cannot"
                                " be found\n")
                            sys.stderr.flush()
            try:
                vl = filewriter.first(entry.open("start_time").read())
                description.append({key: "Start time:", value: vl})
            except Exception:
                sys.stderr.write("nxsfileinfo: start time cannot be found\n")
                sys.stderr.flush()
            try:
                vl = filewriter.first(entry.open("end_time").read())
                description.append({key: "End time:",
                                    value: vl})
            except Exception:
                sys.stderr.write("nxsfileinfo: end time cannot be found\n")
                sys.stderr.flush()
            if "program_name" in entry.names():
                pn = entry.open("program_name")
                pname = filewriter.first(pn.read())
                attr = pn.attributes
                names = [att.name for att in attr]
                if "scan_command" in names:
                    scommand = filewriter.first(attr["scan_command"].read())
                    pname = "%s (%s)" % (pname, scommand)
                description.append({key: "Program:", value: pname})
        return [key, value]

    def show(self, root):
        """ show general informations

        :param root: nexus file root
        :type root: class:`filewriter.FTGroup`
        """

        description = []

        attr = root.attributes

        names = [at.name for at in attr]
        fname = filewriter.first(
            (attr["file_name"].read()
             if "file_name" in names else " ") or " ")
        title = "File name: '%s'" % fname

        print("")
        for en in root:
            description = []
            headers = self.parseentry(en, description)
            ttools = TableTools(description)
            ttools.title = title
            ttools.headers = headers
            rstdescription = ttools.generateList()
            title = ""
            print("\n".join(rstdescription).strip())
            print("")


class BeamtimeLoader(object):

    facilityalias = {
        "PETRA III": "petra3",
        "PETRA IV": "petra4",
    }

    btmdmap = {}

    newbtmdmap = {
        "principalInvestigator": ["applicant.email"],
        # "pid": "beamtimeId",   # ?? is not unique for dataset
        "owner": ["leader.lastname", "applicant.lastname"],
        "contactEmail": ["pi.email", "applicant.email"],
        "sourceFolder": ["corePath"],

        "endTime": ["eventEnd"],    # ?? should be endTime for dataset
        "ownerEmail": ["leader.email", "applicant.email"],
        "description": ["title"],   # ?? should be from dataset
        # "createdAt": ["generated"],  # ?? should be automatic
        # "updatedAt": ["generated"],  # ?? should be automatic
        # "proposalId": "proposalId",
        # "proposalId": ["beamtimeId"],
    }

    oldbtmdmap = {
        "createdAt": ["generated"],  # ?? should be automatic
        "updatedAt": ["generated"],  # ?? should be automatic
    }

    strcre = {
        "creationLocation": "/DESY/{facility}/{beamlineAlias}",
        "instrumentId": "/{facility}/{beamline}",
        "type": "raw",
        "keywords": ["scan"],
        "isPublished": False,
        "proposalId": "{proposalId}.{beamtimeId}",
        "ownerGroup": "{beamtimeId}-dmgt",
        "accessGroups": ["{beamtimeId}-dmgt",
                         "{beamtimeId}-clbt",
                         "{beamtimeId}-part",
                         "{beamline}dmgt",
                         "{beamline}staff"]
    }

    cre = {
        "creationTime": [],  # ?? startTime for dataset !!!
        "ownerGroup": [],  # ??? !!!

        "sampleId": [],  # ???
        "publisheddataId": [],
        "accessGroups": [],  # ???
        "createdBy": [],  # ???
        "updatedBy": [],  # ???
        "createdAt": [],  # ???
        "updatedAt": [],  # ???
        "isPublished": ["false"],
        "dataFormat": [],
        "scientificMetadata": {},
        "orcidOfOwner": "ORCID of owner https://orcid.org "
        "if available",
        "sourceFolderHost": [],
        "size": [],
        "packedSize": [],
        "numberOfFiles": [],
        "numberOfFilesArchived": [],
        "validationStatus": [],
        "keywords": [],
        "datasetName": [],
        "classification": [],
        "license": [],
        "version": [],
        "techniques": [],
        "instrumentId": [],
        "history": [],
        "datasetlifecycle": [],

    }

    dr = {
        "eventStart": [],
        "beamlineAlias": [],
        "leader": [],
        "onlineAnalysis": [],
        "pi.*": [],
        "applicant.*": [],
        "proposalType": [],
        "users": [],
    }

    copymap = {
        "endTime": "scientificMetadata.end_time.value",
        "description": "scientificMetadata.title.value",
        "scientificMetadata.ScanCommand":
            "scientificMetadata.program_name.scan_command",
    }

    copylist = [
        ["creationTime", "endTime"],
    ]

    def __init__(self, options):
        """ loader constructor

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        self.btmdmap = dict(self.newbtmdmap)
        if not hasattr(options, "scicatversion") or \
           int(options.scicatversion) < 4:
            self.btmdmap.update(self.oldbtmdmap)
        self.__pid = options.pid
        self.__pap = options.pap
        self.__idformat = ""
        if hasattr(options, "idformat") and options.idformat:
            self.__idformat = options.idformat
        self.__relpath = options.relpath
        self.__ownergroup = options.ownergroup
        self.__accessgroups = None
        if options.accessgroups is not None:
            self.__accessgroups = options.accessgroups.split(",")

        self.__keywords = []
        if hasattr(options, "keywords") \
           and options.keywords is not None:
            self.__keywords = [
                kw for kw in options.keywords.split(",") if kw]

        dct = {}
        if options.beamtimemeta:
            with open(options.beamtimemeta, "r") as fl:
                # jstr = fl.read()
                # # print(jstr)
                dct = json.load(fl)
        self.__btmeta = dct
        dct = {}
        if options.scientificmeta:
            with open(options.scientificmeta, "r") as fl:
                jstr = fl.read()
                # print(jstr)
                try:
                    dct = json.loads(jstr)
                except Exception:
                    if jstr:
                        nan = float('nan')    # noqa: F841
                        dct = eval(jstr.strip())
        if 'scientificMetadata' in dct.keys():
            self.__scmeta = dct['scientificMetadata']
        else:
            self.__scmeta = dct
        self.__metadata = {}

    def run(self):
        """ runner for DESY beamtime file parser

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """

        if self.__pap:
            self.btmdmap["proposalId"] = ["proposalId"]
        if self.__btmeta:
            for sc, dss in self.btmdmap.items():
                found = False
                for ds in dss:
                    sds = ds.split(".")
                    md = self.__btmeta
                    for sd in sds:
                        if sd in md:
                            md = md[sd]
                        else:
                            break
                    else:
                        self.__metadata[sc] = md
                        found = True
                    if md:
                        break
                    if not found:
                        print("%s cannot be found" % ds)
            strcre2 = dict(self.strcre)
            if self.__idformat:
                strcre2["proposalId"] = self.__idformat
            for sc, vl in strcre2.items():
                if isinstance(vl, list):
                    self.__metadata[sc] = [
                        (vv.format(**self.__btmeta)
                         if hasattr(vv, "format") else vv)
                        for vv in vl
                    ]
                else:
                    if hasattr(vl, "format"):
                        self.__metadata[sc] = vl.format(**self.__btmeta)
                    else:
                        self.__metadata[sc] = vl
        if self.__relpath and "sourceFolder" in self.__metadata:
            self.__metadata["sourceFolder"] = \
                os.path.join(self.__metadata["sourceFolder"], self.__relpath)
        if self.__scmeta or self.__btmeta:
            self.__metadata["scientificMetadata"] = {}
        if self.__scmeta:
            self.__metadata["scientificMetadata"].update(self.__scmeta)
        if self.__btmeta and \
           "beamtimeId" not in self.__metadata["scientificMetadata"]:
            self.__metadata["scientificMetadata"]["beamtimeId"] = \
                self.__btmeta["beamtimeId"]
        if self.__btmeta and \
           "DOOR_proposalId" not in self.__metadata["scientificMetadata"]:
            self.__metadata["scientificMetadata"]["DOOR_proposalId"] = \
                self.__btmeta["proposalId"]
        if self.__pid:
            self.__metadata["pid"] = self.__pid
        if self.__ownergroup:
            self.__metadata["ownerGroup"] = self.__ownergroup
        if self.__accessgroups is not None:
            self.__metadata["accessGroups"] = self.__accessgroups
        if self.__keywords:
            if "keywords" not in self.__metadata:
                self.__metadata["keywords"] = []
            self.__metadata["keywords"].extend(self.__keywords)
        # print(self.__metadata)
        return self.__metadata

    def merge(self, metadata):
        """ update metadata with dictionary

        :param metadata: metadata dictionary to merge in
        :type metadata: :obj:`dict` <:obj:`str`, `any`>
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        if not self.__metadata:
            return metadata
        elif not metadata:
            return metadata
        return dict(self._mergedict(metadata, self.__metadata))

    def merge_copy_maps(self, cmap):
        """ merge copy maps

        :param cmap: overwrite dictionary
        :type cmap: :obj:`dict` <:obj:`str`, :obj:`str`>
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        if cmap is None:
            cpmap = dict(self.copymap)
        else:
            cpmap = dict(self.copymap)
            cpmap.update(cmap)
        return cpmap

    def merge_copy_lists(self, clist):
        """ merge copy lists

        :param clist: overwrite copy list
        :type cmap: :obj:`list` < [:obj:`str`, :obj:`str`] >
        :returns: metadata dictionary
        :rtype: :obj:`list` < [:obj:`str`, :obj:`str`] >
        """
        if clist is None:
            cplist = list(self.copylist)
        else:
            cplist = list(self.copylist)
            cplist.extend(clist)
        return cplist

    def append_copymap_field(self, metadata, cmap, clist, cmapfield=None):
        """ overwrite metadata with dictionary

        :param metadata: metadata dictionary to merge in
        :type metadata: :obj:`dict` <:obj:`str`, `any`>
        :param cmap: overwrite dictionary
        :type cmap: :obj:`dict` <:obj:`str`, :obj:`str`>
        :param clist: copy list to overwrite metadata
        :type clist: :obj:`list` < [:obj:`str`, :obj:`str`] >
        :param cmapfield: copy map nexus field
        :type cmapfield: :obj:`str`
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        if cmapfield and metadata and cmap:
            vls = cmapfield.split(".")
            md = metadata
            for vl in vls:
                if vl in md:
                    md = md[vl]
                else:
                    break
            else:
                if md:
                    try:
                        dct = yaml.safe_load(str(md).strip())
                        if dct and isinstance(dct, dict):
                            cmap.update(dct)
                        elif dct:
                            if isinstance(dct, basestring):
                                dct = getlist(str(md).strip())
                            if isinstance(dct, list):
                                for line in dct:
                                    if isinstance(line, list):
                                        clist.append(line[:2])
                    except Exception as e:
                        sys.stderr.write(
                            "nxsfileinfo: copymap update: '%s'\n"
                            % str(e))

    def overwrite(self, metadata, cmap=None, clist=None, cmapfield=None):
        """ overwrite metadata with dictionary

        :param metadata: metadata dictionary to merge in
        :type metadata: :obj:`dict` <:obj:`str`, `any`>
        :param cmap: copy map to overwrite dictionary
        :type cmap: :obj:`dict` <:obj:`str`, :obj:`str`>
        :param clist: copy list to overwrite metadata
        :type clist: :obj:`list` < [:obj:`str`, :obj:`str`] >
        :param cmapfield: copy map nexus field
        :type cmapfield: :obj:`str`
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        cpmap = self.merge_copy_maps(cmap)
        cplist = self.merge_copy_lists(clist)
        self.append_copymap_field(metadata, cpmap, cplist, cmapfield)
        if metadata:
            for ts, vs in cpmap.items():
                if ts and vs and isinstance(ts, basestring) \
                   and isinstance(vs, basestring) \
                   and not ts.startswith(vs + "."):
                    vls = vs.split(".")
                    md = metadata
                    for vl in vls:
                        if vl in md:
                            md = md[vl]
                        else:
                            break
                    else:
                        tgs = ts.split(".")
                        td = metadata
                        parent = None
                        for tg in tgs:
                            parent = td
                            if tg in td:
                                td = td[tg]
                            else:
                                td[tg] = {}
                                td = td[tg]
                        parent[tg] = md
            for line in cplist:
                if line and len(line) > 1 and line[0] and line[1] and \
                   isinstance(line[0], basestring) and \
                   isinstance(line[1], basestring) and \
                   not line[0].startswith(line[1] + "."):
                    action = None
                    if line and len(line) > 2 and line[2] and \
                            isinstance(line[2], basestring):
                        action = line[2]
                    ts = line[0]
                    vs = line[1]
                    vls = vs.split(".")
                    md = metadata
                    for vl in vls:
                        if vl in md:
                            md = md[vl]
                        else:
                            break
                    else:
                        tgs = ts.split(".")
                        td = metadata
                        parent = None
                        for tg in tgs:
                            parent = td
                            if tg in td:
                                td = td[tg]
                            else:
                                td[tg] = {}
                                td = td[tg]
                        if action and action.lower() \
                                in ["extend", "append", "e", "a"]:
                            if tg not in parent:
                                parent[tg] = []
                            elif not isinstance(parent[tg], list):
                                parent[tg] = [parent[tg]]
                            if action.lower() in ["extend", "e"] and \
                                    type(md).__name__ in ["list", "ndarray"]:
                                parent[tg].extend(md)
                            else:
                                parent[tg].append(md)

                        else:
                            parent[tg] = md
        return metadata

    def remove_metadata(self, metadata, cmap=None, clist=None, cmapfield=None):
        """ remove metadata with dictionary with empty input or output
            in the copy map

        :param metadata: metadata dictionary to merge in
        :type metadata: :obj:`dict` <:obj:`str`, `any`>
        :param cmap: overwrite dictionary
        :type cmap: :obj:`dict` <:obj:`str`, :obj:`str`>
        :param clist: copy list to overwrite metadata
        :type clist: :obj:`list` < [:obj:`str`, :obj:`str`] >
        :param cmapfield: copy map nexus field
        :type cmapfield: :obj:`str`
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        cpmap = self.merge_copy_maps(cmap)
        cplist = list(clist or [])
        self.append_copymap_field(metadata, cpmap, cplist, cmapfield)
        if metadata:
            for ts, vs in cpmap.items():
                vv = None
                if not ts:
                    vv = vs
                if not vs:
                    vv = ts
                if vv and isinstance(vv, basestring):
                    vls = vv.split(".")
                    md = metadata
                    parent = None
                    for vl in vls:
                        parent = md
                        if vl in md:
                            md = md[vl]
                        else:
                            break
                    else:
                        parent.pop(vl)
            for line in cplist:
                vv = None
                if line:
                    if len(line) == 1 and line[0]:
                        vv = line[0]
                    elif len(line) > 1:
                        if line[0] and not line[1]:
                            vv = line[0]
                        if line[1] and not line[0]:
                            vv = line[1]
                    if vv and isinstance(vv, basestring):
                        vls = vv.split(".")
                        md = metadata
                        parent = None
                        for vl in vls:
                            parent = md
                            if vl in md:
                                md = md[vl]
                            else:
                                break
                        else:
                            parent.pop(vl)
        return metadata

    @classmethod
    def _mergedict(cls, dct1, dct2):
        for key in set(dct1) | set(dct2):
            if key in dct1 and key in dct2:
                if isinstance(dct1[key], dict) and isinstance(dct2[key], dict):
                    yield (key, dict(cls._mergedict(dct1[key], dct2[key])))
                else:
                    yield (key, dct2[key])
            elif key in dct1:
                yield (key, dct1[key])
            else:
                yield (key, dct2[key])

    def update_pid(self, metadata, filename=None, puuid=False, pfname=False,
                   beamtimeid=None):
        """ update pid metadata with dictionary

        :param metadata: metadata dictionary to merge in
        :type metadata: :obj:`dict` <:obj:`str`, `any`>
        :param filename: nexus filename
        :type filename: :obj:`str`
        :param puuid: pid with uuid
        :type puuid: :obj:`bool`
        :param pfname: pid with file name
        :type pfname: :obj:`bool`
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        metadata = metadata or {}
        genuid = False
        if "pid" not in metadata:
            beamtimeid = beamtimeid or ""
            if not beamtimeid and "scientificMetadata" in metadata \
               and "beamtimeId" in metadata["scientificMetadata"]:
                beamtimeid = metadata["scientificMetadata"]["beamtimeId"]
            scanid = ""
            fsscanid = ""
            fiscanid = None
            fname = ""
            if filename:
                fdir, fname = os.path.split(filename)
                fname, fext = os.path.splitext(fname)
                lfl = fname.split("_")
                fsscanid = lfl[-1]
                res = re.search(r'\d+$', fsscanid)
                fiscanid = int(res.group()) if res else None
            esscanid = ""
            eiscanid = None
            lfl = None
            if "scientificMetadata" in metadata and \
               "name" in metadata["scientificMetadata"] and \
               metadata["scientificMetadata"]["name"]:
                lfl = metadata["scientificMetadata"]["name"].split("_")
                esscanid = lfl[-1]
                res = re.search(r'\d+$', esscanid)
                eiscanid = int(res.group()) if res else None
                # if eiscanid:
                #     print("WWWW:", eiscanid)
            if not pfname and fname and fiscanid is not None:
                scanid = fname
            elif not pfname and fname and eiscanid is not None:
                scanid = "%s_%s" % (fname, eiscanid)
            elif not pfname and fname:
                scanid = fname
            elif fiscanid is not None:
                scanid = str(fiscanid)
            elif eiscanid is not None:
                scanid = str(eiscanid)
            elif fsscanid and esscanid and esscanid == fsscanid:
                scanid = esscanid
            elif fsscanid and esscanid and esscanid != fsscanid:
                scanid = "%s_%s" % (fsscanid, esscanid)
            elif fsscanid:
                scanid = fsscanid
            else:
                scanid = esscanid
            if beamtimeid and scanid:
                if puuid:
                    metadata["pid"] = "%s/%s/%s" % \
                        (beamtimeid, scanid, str(uuid.uuid4()))
                    genuid = True
                else:
                    metadata["pid"] = "%s/%s" % \
                        (beamtimeid, scanid)

        if "datasetName" not in metadata and "pid" in metadata:
            spid = metadata["pid"].split("/")
            if genuid:
                spid = spid[:-1]
            if len(spid) == 2:
                metadata["datasetName"] = spid[1]
            elif len(spid) > 1:
                try:
                    int(spid[-1])
                    metadata["datasetName"] = spid[-2]
                except Exception:
                    metadata["datasetName"] = spid[-1]
            else:
                metadata["datasetName"] = metadata["pid"]
        return metadata

    def update_sampleid(self, metadata, sampleid=None, sidfromname=False):
        """ update sampleid

        :param metadata: metadata dictionary to merge in
        :type metadata: :obj:`dict` <:obj:`str`, `any`>
        :param sampleid: sample id
        :type sampleid: :obj:`str`
        :param sidfromname: sample id from its name
        :type sidfromname: :obj:`bool`
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        if sampleid:
            metadata["sampleId"] = sampleid
        elif sidfromname:
            if "scientificMetadata" in metadata and \
               "sample" in metadata["scientificMetadata"] and \
               "name" in metadata["scientificMetadata"]["sample"]:
                sname = metadata["scientificMetadata"]["sample"]["name"]
                if isinstance(sname, dict):
                    if "value" in sname.keys() and sname["value"]:
                        metadata["sampleId"] = sname["value"]
                elif sname:
                    metadata["sampleId"] = sname
        else:
            try:
                if "scientificMetadata" in metadata and \
                   "sample" in metadata["scientificMetadata"] and \
                   "description" in metadata["scientificMetadata"]["sample"]:
                    gdes = \
                        metadata["scientificMetadata"]["sample"]["description"]
                    if "value" in gdes:
                        sampleid = None
                        try:
                            des = yaml.safe_load(gdes["value"])
                            if "sample_id" in des:
                                sampleid = des["sample_id"]
                            elif "sampleId" in des:
                                sampleid = des["sampleId"]
                            else:
                                sampleid = gdes["value"]
                        except Exception:
                            sampleid = gdes["value"]
                        if sampleid:
                            metadata["sampleId"] = sampleid
            except Exception as e:
                sys.stderr.write("nxsfileinfo: '%s'\n"
                                 % str(e))
        return metadata

    def update_instrumentid(self, metadata):
        """ update instrument id

        :param metadata: metadata dictionary to merge in
        :type metadata: :obj:`dict` <:obj:`str`, `any`>
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        if "instrumentId" in metadata:
            ins = metadata["instrumentId"]
            for fac, alias in self.facilityalias.items():
                ins = ins.replace(fac, alias)
            ins = ins.lower()
            metadata["instrumentId"] = ins
        return metadata

    def update_techniques(self, metadata, techniques=None):
        """ update techniques

        :param metadata: metadata dictionary to merge in
        :type metadata: :obj:`dict` <:obj:`str`, `any`>
        :param techniques: a list of techniques splitted by comma
        :type techniques: :obj:`str`
        :returns: metadata dictionary
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        if techniques:
            metadata["techniques"] = \
                self.generate_techniques(techniques.split(","))
        if metadata and "techniques" not in metadata:
            try:
                if "scientificMetadata" in metadata and \
                       "definition" in metadata["scientificMetadata"]:
                    gdefin = metadata["scientificMetadata"]["definition"]
                    if "value" in gdefin:
                        defin = gdefin["value"].split(",")
                        defin = [
                            (df[2:]
                             if (df and str(df).startswith("NX")) else df)
                            for df in defin]
                        if defin:
                            metadata["techniques"] = \
                                self.generate_techniques(defin)
            except Exception as e:
                sys.stderr.write("nxsfileinfo: '%s'\n"
                                 % str(e))

            try:
                if "scientificMetadata" in metadata and \
                       "experiment_description" in \
                       metadata["scientificMetadata"]:
                    gexpdes = \
                        metadata["scientificMetadata"][
                            "experiment_description"]
                    if "value" in gexpdes:
                        try:
                            pids = None
                            tes = None
                            expdes = yaml.safe_load(gexpdes["value"])
                            if "techniques" in expdes:
                                tes = expdes["techniques"]
                            elif "technique" in expdes:
                                tes = [expdes["technique"]]
                            if "techniques_pids" in expdes:
                                pids = expdes["techniques_pids"]
                            elif "technique_pid" in expdes:
                                pids = [expdes["technique_pid"]]
                            if tes is not None and pids is not None:
                                metadata["techniques"] = \
                                    self.generate_techniques(tes, pids)
                            elif tes is not None:
                                metadata["techniques"] = \
                                    self.generate_techniques(tes)
                            elif pids is not None:
                                metadata["techniques"] = \
                                    self.generate_techniques(pids)
                            else:
                                metadata["techniques"] = \
                                    self.generate_techniques(
                                        [gexpdes["value"]])
                        except Exception:
                            metadata["techniques"] = \
                                self.generate_techniques(
                                    [gexpdes["value"]])
            except Exception as e:
                sys.stderr.write("nxsfileinfo: '%s'\n"
                                 % str(e))

        if metadata and "techniques" not in metadata:
            metadata["techniques"] = []
        return metadata

    def generate_techniques(self, techniques, techniques_pids=None):
        """ generate technique dictionary

        :param techniques: a list of techniques splitted by comma
        :type techniques: :obj:`list` <:obj:`str`>
        :param techniques_pids: a list of technique pids splitted by comma
        :type techniques_pids: :obj:`list` <:obj:`str`>
        :returns: technique dictionary
        :rtype: :obj:`dict` <:obj:`str`, `objstr`>
        """
        result = []
        # print(techniques)
        # print(techniques_pids)
        for it, te in enumerate(techniques):
            pid = None
            name = te
            if techniques_pids and len(techniques_pids) > it and \
               techniques_pids[it] is not None:
                pid = techniques_pids[it]
            elif te.startswith("http:/") and te in id_techniques.keys():
                pid = te
                name = id_techniques[pid]
            elif te in nexus_panet.keys():
                pid = nexus_panet[te]
                name = id_techniques[pid]
            elif te.startswith("PaNET"):
                nm = "http://purl.org/pan-science/PaNET/%s" % te
                if nm in id_techniques.keys():
                    pid = nm
                    name = id_techniques[pid]
            if pid:
                result.append({"pid": pid, "name": name})
            elif name:
                result.append({"pid": name, "name": name})
        # print(result)
        return result


class Metadata(Runner):

    """ Metadata runner"""

    #: (:obj:`str`) command description
    description = "show metadata information for the nexus file"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsfileinfo metadata /user/data/myfile.nxs\n" \
        + "       nxsfileinfo metadata /user/data/myfile.fio\n" \
        + "       nxsfileinfo metadata /user/data/myfile.nxs -p 'Group'\n" \
        + "       nxsfileinfo metadata /user/data/myfile.nxs -s\n" \
        + "       nxsfileinfo metadata /user/data/myfile.nxs " \
        + "-a units,NX_class\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        self._parser.add_argument(
            "-a", "--attributes",
            help="names of field or group attributes to be show "
            " (separated by commas without spaces). "
            "The default takes all attributes",
            dest="attrs", default=None)
        self._parser.add_argument(
            "-n", "--hidden-attributes",
            help="names of field or group attributes to be hidden "
            " (separated by commas without spaces). "
            "The default: 'nexdatas_source,nexdatas_strategy,units'",
            dest="nattrs", default="nexdatas_source,nexdatas_strategy,units")
        self._parser.add_argument(
            "-v", "--values",
            help="field names of more dimensional datasets"
            " which value should be shown"
            " (separated by commas without spaces)",
            dest="values", default="")
        self._parser.add_argument(
            "-w", "--owner-group",
            default="", dest="ownergroup",
            help="owner group name. Default is {beamtimeid}-dmgt")
        self._parser.add_argument(
            "-c", "--access-groups",
            default=None, dest="accessgroups",
            help="access group names separated by commas. "
            "Default is {beamtimeId}-dmgt,{beamtimeid}-clbt,{beamtimeId}-part,"
            "{beamline}dmgt,{beamline}staff")
        self._parser.add_argument(
            "-z", "--keywords",
            default=None, dest="keywords",
            help="dataset keywords separated by commas.")
        self._parser.add_argument(
            "-g", "--group-postfix",
            help="postfix to be added to NeXus group name. "
            "The default: ''",
            dest="group_postfix", default="")
        self._parser.add_argument(
            "-t", "--entry-classes",
            help="names of entry NX_class to be shown"
            " (separated by commas without spaces)."
            " If name is '' all groups are shown. "
            "The default: 'NXentry'",
            dest="entryclasses", default="NXentry")
        self._parser.add_argument(
            "-e", "--entry-names",
            help="names of entry groups to be shown"
            " (separated by commas without spaces)."
            " If name is '' all groups are shown. "
            "The default: ''",
            dest="entrynames", default="")
        self._parser.add_argument(
            "-q", "--techniques",
            help="names of techniques"
            " (separated by commas without spaces)."
            "The default: ''",
            dest="techniques", default="")
        self._parser.add_argument(
            "-j", "--sample-id",
            help="sampleId",
            dest="sampleid", default="")
        self._parser.add_argument(
            "--sample-id-from-name", action="store_true",
            default=False, dest="sampleidfromname",
            help="get sampleId from the sample name")
        self._parser.add_argument(
            "-y", "--instrument-id",
            help="instrumentId",
            dest="instrumentid", default="")
        self._parser.add_argument(
            "--raw-instrument-id", action="store_true",
            default=False, dest="rawinstrumentid",
            help="leave raw instrument id")
        self._parser.add_argument(
            "-m", "--raw-metadata", action="store_true",
            default=False, dest="rawscientific",
            help="do not store NXentry as scientificMetadata")
        self._parser.add_argument(
            "--dont-merge", action="store_true",
            default=False, dest="dontmerge",
            help="keep entries separate")
        self._parser.add_argument(
            "--add-empty-units", action="store_true",
            default=False, dest="emptyunits",
            help="add empty units for fields without units")
        self._parser.add_argument(
            "--oned", action="store_true",
            default=False, dest="oned",
            help="add 1d values to scientificMetadata")
        self._parser.add_argument(
            "--max-oned-size",
            default=1024, dest="maxonedsize",
            help="add max and min (or first and last)"
            " values of 1d records "
            "to scientificMetadata "
            "if its size excides --max-oned-size value")
        self._parser.add_argument(
            "-p", "--pid", dest="pid",
            help=("dataset pid"))
        self._parser.add_argument(
            "-i", "--beamtimeid", dest="beamtimeid",
            help=("beamtime id"))
        self._parser.add_argument(
            "--id-format", dest="idformat",
            default="{beamtimeId}",
            # default="{proposalId}.{beamtimeId}",
            help=("format of scicat proposal id. "
                  "Default is {beamtimeId}"))
        self._parser.add_argument(
            "-u", "--pid-with-uuid", action="store_true",
            default=False, dest="puuid",
            help=("generate pid with uuid"))
        self._parser.add_argument(
            "-d", "--pid-without-filename", action="store_true",
            default=False, dest="pfname",
            help=("generate pid without file name"))
        self._parser.add_argument(
            "-f", "--file-format", dest="fileformat",
            help=("input file format, e.g. 'nxs'. "
                  "Default is defined by the file extension"))
        self._parser.add_argument(
            "--proposal-as-proposal", action="store_true",
            default=False, dest="pap",
            help=("Store the DESY proposal as the SciCat proposal"))
        self._parser.add_argument(
            "-k", "--scicat-version",
            default=4, dest="scicatversion",
            help="major scicat version metadata")
        self._parser.add_argument(
            "--h5py", action="store_true",
            default=False, dest="h5py",
            help="use h5py module as a nexus reader")
        self._parser.add_argument(
            "--h5cpp", action="store_true",
            default=False, dest="h5cpp",
            help="use h5cpp module as a nexus reader")
        self._parser.add_argument(
            "-x", "--chmod", dest="chmod",
            help=("json metadata file mod bits, e.g. 0o662"))
        self._parser.add_argument(
            "--copy-map", dest="copymap",
            help=("json or yaml map of {output: input} "
                  "or [[output, input],]  or a text file list "
                  " to re-arrange metadata"))
        self._parser.add_argument(
            "--copy-map-field", dest="copymapfield",
            help=(
                "field json or yaml with map {output: input} "
                "or [[output, input],] or a text file list "
                "to re-arrange metadata."
                " The default: "
                "'scientificMetadata.nxsfileinfo_parameters.copymap.value'"),
            default='scientificMetadata.nxsfileinfo_parameters.copymap.value')
        self._parser.add_argument(
            "--copy-map-error", action="store_true",
            default=False, dest="copymaperror",
            help=("Raise an error when the copy map file does not exist"))

    def postauto(self):
        """ parser creator after autocomplete run """
        self._parser.add_argument(
            "-b", "--beamtime-meta", dest="beamtimemeta",
            help=("beamtime metadata file"))
        self._parser.add_argument(
            "-s", "--scientific-meta", dest="scientificmeta",
            help=("scientific metadata file"))
        self._parser.add_argument(
            "-l", "--copy-map-file", dest="copymapfile",
            help=("json or yaml file containing the copy map, "
                  "see also --copy-map"))
        self._parser.add_argument(
            "-o", "--output", dest="output",
            help=("output scicat metadata file"))
        self._parser.add_argument(
            "-r", "--relative-path", dest="relpath",
            help=("relative path to the scan files"))
        self._parser.add_argument(
            'args', metavar='nexus_file', type=str, nargs="*",
            help='new nexus file name')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        if options.h5cpp:
            writer = "h5cpp"
        elif options.h5py:
            writer = "h5py"
        elif "h5cpp" in WRITERS.keys():
            writer = "h5cpp"
        else:
            writer = "h5py"
        if (options.h5cpp and options.h5py) or writer not in WRITERS.keys():
            sys.stderr.write("nxsfileinfo: Writer '%s' cannot be opened\n"
                             % writer)
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)

        root = None
        nxfl = None
        if not hasattr(options, "fileformat"):
            options.fileformat = ""
        if hasattr(options, "maxonedsized"):
            try:
                options.maxonedsize = int(options.maxonedsize)
            except Exception:
                sys.stderr.write(
                    "nxsfileinfo: Max 1d size '%s' cannot be "
                    "converted to int\n" % options.maxonedsize)
                sys.stderr.flush()
                self._parser.print_help()
                sys.exit(255)
        if options.args:
            wrmodule = WRITERS[writer.lower()]
            if not options.fileformat:
                rt, ext = os.path.splitext(options.args[0])
                if ext and len(ext) > 1 and ext.startswith("."):
                    options.fileformat = ext[1:]
            try:
                if options.fileformat in ['nxs', 'h5', 'nx', 'ndf']:
                    nxfl = filewriter.open_file(
                        options.args[0], readonly=True,
                        writer=wrmodule)
                    root = nxfl.root()
                elif options.fileformat in ['fio']:
                    with open(options.args[0]) as fl:
                        root = fl.read()
            except Exception:
                sys.stderr.write("nxsfileinfo: File '%s' cannot be opened\n"
                                 % options.args[0])
                sys.stderr.flush()
                self._parser.print_help()
                sys.exit(255)

        self.show(root, options)
        if nxfl is not None:
            nxfl.close()

    @classmethod
    def _cure(cls, result):
        if 'creationTime' not in result:
            result['creationTime'] = isoDate(filewriter.FTFile.currenttime())
        else:
            result['creationTime'] = isoDate(result['creationTime'])
        if 'endTime' in result:
            result['endTime'] = isoDate(result['endTime'])

        if 'type' not in result:
            result['type'] = 'raw'
        if 'creationLocation' not in result:
            result['creationLocation'] = "/DESY/PETRA III"
        if 'ownerGroup' not in result:
            result['ownerGroup'] = "ingestor"
        return result

    @classmethod
    def _merge(cls, resultlist):
        if not isinstance(resultlist, list):
            return resultlist
        elif len(resultlist) == 0:
            return {}
        elif len(resultlist) == 1:
            return resultlist[0]
        result = resultlist[0]
        for rs in resultlist[1:]:
            result = dict(BeamtimeLoader._mergedict(result, rs))
        return result

    @classmethod
    def metadata(cls, root, options):
        """ get metadata from nexus and beamtime file

        :param root: nexus file root
        :type root: :class:`filewriter.FTGroup`
        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: nexus file root metadata
        :rtype: :obj:`str`
        """
        values = []
        attrs = None
        entryclasses = []
        entrynames = []
        usercopymap = {}
        usercopylist = []

        if options.values:
            values = options.values.split(',')

        if options.attrs:
            attrs = options.attrs.split(',')
        elif options.attrs is not None:
            attrs = []

        if options.nattrs not in [None, '', "''", '""']:
            nattrs = options.nattrs.split(',')
        else:
            nattrs = []

        if options.entryclasses not in [None, '', "''", '""']:
            entryclasses = options.entryclasses.split(',')

        if options.entrynames not in [None, '', "''", '""']:
            entrynames = options.entrynames.split(',')

        copymapfield = None
        if hasattr(options, "copymapfield") and options.copymapfield:
            copymapfield = options.copymapfield

        if hasattr(options, "copymap") and options.copymap:
            dct = yaml.safe_load(options.copymap.strip())
            if dct and isinstance(dct, dict):
                usercopymap.update(dct)
            elif dct:
                if isinstance(dct, basestring):
                    dct = getlist(options.copymap.strip())
                if isinstance(dct, list):
                    for line in dct:
                        if isinstance(line, list):
                            usercopylist.append(line[:3])

        if hasattr(options, "copymapfile") and options.copymapfile:
            if os.path.isfile(options.copymapfile):
                with open(options.copymapfile, "r") as fl:
                    jstr = fl.read()
                    # print(jstr)
                    try:
                        dct = yaml.safe_load(jstr.strip())
                    except Exception:
                        if jstr:
                            nan = float('nan')    # noqa: F841
                            try:
                                dct = eval(jstr.strip())
                            except Exception:
                                dct = " "
                            # mdflatten(dstr, [], dct)
                        else:
                            dct = ""
                    if dct and isinstance(dct, dict):
                        usercopymap.update(dct)
                    elif dct:
                        if isinstance(dct, basestring):
                            dct = getlist(jstr.strip())
                        if isinstance(dct, list):
                            for line in dct:
                                if isinstance(line, list):
                                    usercopylist.append(line[:3])
            elif hasattr(options, "copymaperror") and options.copymaperror:
                raise Exception("Copy-map file '%s' does not exist"
                                % options.copymapfile)

        result = None
        nxsparser = None
        if not hasattr(options, "fileformat"):
            options.fileformat = ""
        if options.args and not options.fileformat:
            rt, ext = os.path.splitext(options.args[0])
            if ext and len(ext) > 1 and ext.startswith("."):
                options.fileformat = ext[1:]
        if root is not None:
            if options.fileformat in ['nxs', 'h5', 'nx', 'ndf']:
                nxsparser = NXSFileParser(root)
                nxsparser.valuestostore = values
                nxsparser.group_postfix = options.group_postfix
                nxsparser.entryclasses = entryclasses
                nxsparser.entrynames = entrynames
                nxsparser.scientific = not options.rawscientific
                if hasattr(options, "emptyunits"):
                    nxsparser.emptyunits = options.emptyunits
                nxsparser.attrs = attrs
                nxsparser.hiddenattrs = nattrs
                if hasattr(options, "oned"):
                    nxsparser.oned = options.oned
                if hasattr(options, "maxonedsize"):
                    nxsparser.maxonedsize = int(options.maxonedsize)
                nxsparser.parseMeta()
            elif options.fileformat in ['fio']:
                nxsparser = FIOFileParser(root)
                nxsparser.group_postfix = options.group_postfix
                # nxsparser.attrs = attrs
                # nxsparser.hiddenattrs = nattrs
                if hasattr(options, "oned"):
                    nxsparser.oned = options.oned
                if hasattr(options, "maxonedsize"):
                    nxsparser.maxonedsize = int(options.maxonedsize)
                nxsparser.parseMeta()

        if nxsparser is None:
            bl = BeamtimeLoader(options)
            result = bl.run()
            result = bl.overwrite(
                result,
                usercopymap or None,
                usercopylist or None,
                copymapfield)
            result = bl.update_pid(
                result, None, options.puuid,
                options.pfname, options.beamtimeid)
            if not options.rawscientific:
                techniques = None
                if hasattr(options, "techniques"):
                    techniques = options.techniques
                result = bl.update_techniques(result, techniques)

                sampleid = None
                if hasattr(options, "sampleid"):
                    sampleid = options.sampleid
                sid_from_name = None
                if hasattr(options, "sampleidfromname"):
                    sid_from_name = options.sampleidfromname
                result = bl.update_sampleid(result, sampleid, sid_from_name)
                rawinstrumentid = None
                if hasattr(options, "rawinstrumentid"):
                    rawinstrumentid = options.rawinstrumentid
                if hasattr(options, "instrumentid"):
                    instrumentid = options.instrumentid
                    if instrumentid:
                        result["instrumentId"] = instrumentid
                    elif "instrumentId" in result and \
                         result["instrumentId"] and not rawinstrumentid:
                        result = bl.update_instrumentid(result)
            result = bl.remove_metadata(
                result, usercopymap or None,
                usercopylist or None, copymapfield)
            if not options.rawscientific:
                result = cls._cure(result)
        elif nxsparser and nxsparser.description:
            if len(nxsparser.description) == 1:
                desc = nxsparser.description[0]
                if not options.beamtimemeta:
                    try:
                        if "scientificMetadata" in desc \
                           and "experiment_identifier" in \
                           desc["scientificMetadata"] \
                           and "beamtime_filename" in \
                           desc["scientificMetadata"][
                               "experiment_identifier"]:
                            options.beamtimemeta = \
                                desc["scientificMetadata"][
                                    "experiment_identifier"][
                                        "beamtime_filename"]
                    except Exception:
                        pass
                bl = BeamtimeLoader(options)
                bl.run()
                result = bl.merge(desc)
                result = bl.overwrite(
                    result, usercopymap or None,
                    usercopylist or None, copymapfield)
                result = bl.update_pid(
                    result, options.args[0], options.puuid,
                    options.pfname, options.beamtimeid)
                if not options.rawscientific:
                    techniques = None
                    if hasattr(options, "techniques"):
                        techniques = options.techniques
                    result = bl.update_techniques(result, techniques)

                    sampleid = None
                    if hasattr(options, "sampleid"):
                        sampleid = options.sampleid
                    sid_from_name = None
                    if hasattr(options, "sampleidfromname"):
                        sid_from_name = options.sampleidfromname
                    result = bl.update_sampleid(
                        result, sampleid, sid_from_name)
                    rawinstrumentid = None
                    if hasattr(options, "rawinstrumentid"):
                        rawinstrumentid = options.rawinstrumentid
                    if hasattr(options, "instrumentid"):
                        instrumentid = options.instrumentid
                        if instrumentid:
                            result["instrumentId"] = instrumentid
                        elif "instrumentId" in result and \
                             result["instrumentId"] and not rawinstrumentid:
                            result = bl.update_instrumentid(result)
                result = bl.remove_metadata(
                    result, usercopymap or None,
                    usercopylist or None, copymapfield)
                if not options.rawscientific:
                    result = cls._cure(result)
            else:
                result = []
                for desc in nxsparser.description:
                    if not options.beamtimemeta:
                        try:
                            if "scientificMetadata" in desc \
                               and "experimental_identifier" in \
                               desc["scientificMetadata"] \
                               and "beamtime_filename" in \
                               desc["scientificMetadata"][
                                   "experimental_identifier"]:
                                options.beamtimemeta = \
                                    desc["scientificMetadata"][
                                        "experimental_identifier"][
                                            "beamtime_filename"]
                        except Exception:
                            pass
                    bl = BeamtimeLoader(options)
                    bl.run()
                    rst = bl.merge(desc)
                    rst = bl.overwrite(
                        rst, usercopymap or None,
                        usercopylist or None, copymapfield)
                    rst = bl.update_pid(
                        rst, options.args[0], options.puuid,
                        options.pfname, options.beamtimeid)
                    if not options.rawscientific:
                        techniques = None
                        if hasattr(options, "techniques"):
                            techniques = options.techniques
                        rst = bl.update_techniques(rst, techniques)
                        sampleid = None
                        if hasattr(options, "sampleid"):
                            sampleid = options.sampleid
                        sid_from_name = None
                        if hasattr(options, "sampleidfromname"):
                            sid_from_name = options.sampleidfromname
                        rst = bl.update_sampleid(
                            rst, sampleid, sid_from_name)
                        if hasattr(options, "rawinstrumentid"):
                            rawinstrumentid = options.rawinstrumentid
                        if hasattr(options, "instrumentid"):
                            instrumentid = options.instrumentid
                            if instrumentid:
                                rst["instrumentId"] = instrumentid
                            elif "instrumentId" in rst and \
                                 rst["instrumentId"] and not rawinstrumentid:
                                rst = bl.update_instrumentid(rst)
                    rst = bl.remove_metadata(
                        rst, usercopymap or None,
                        usercopylist or None, copymapfield)
                    if not options.rawscientific:
                        rst = cls._cure(rst)
                    result.append(rst)
                if not options.rawscientific and not options.dontmerge:
                    result = cls._merge(result)
        if result is not None:
            return json.dumps(
                result, sort_keys=True, indent=4,
                cls=numpyEncoderNull)

    def show(self, root, options):
        """ the main function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :param root: nexus file root
        :type root: :class:`filewriter.FTGroup`
        """
        try:
            metadata = self.metadata(root, options)
            if metadata:
                if options.output:
                    fdir, fn = os.path.split(os.path.abspath(options.output))
                    if not os.path.isdir(fdir):
                        os.makedirs(fdir, exist_ok=True)
                    chmod = None
                    try:
                        chmod = int(options.chmod, 8)
                    except Exception:
                        options.chmod = None

                    if options.chmod:
                        oldmask = os.umask(0)

                        def opener(path, flags):
                            return os.open(path, flags, chmod)

                        try:
                            with open(options.output,
                                      "w", opener=opener) as fl:
                                fl.write(metadata)
                        except Exception:
                            with open(options.output, "w") as fl:
                                fl.write(metadata)
                            os.chmod(options.output, chmod)
                        os.umask(oldmask)
                    else:
                        with open(options.output, "w") as fl:
                            fl.write(metadata)
                else:
                    print(metadata)
        except Exception as e:
            sys.stderr.write("nxsfileinfo: '%s'\n"
                             % str(e))
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)


class GroupMetadata(Runner):

    """ Group Metadata runner"""

    #: (:obj:`str`) command description
    description = "group scan metadata information"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsfileinfo groupmetadata" \
        + " -o /user/data/myscan.scan.json " \
        + " -t /user/data/myscan.attachment.json " \
        + " -l /user/data/myscan.origdatablock.json " \
        + " -c /home/user/group_config.txt " \
        + " -m /user/data/myscan_00023.scan.json " \
        + " -d /user/data/myscan_00023.origdatablock.json " \
        + " -a /user/data/myscan_00023.attachment.json \n" \
        + " \n" \
        + "       nxsfileinfo groupmetadata myscan_m001 " \
        " -m /user/data/myscan_00021.scan.json\n" \
        + "  -c /home/user/group_config.txt " \
        + " \n" \
        + " \n" \
        + "       nxsfileinfo groupmetadata  myscan_m001 " \
        + " -c /home/user/group_config.txt " \
        + " -m /user/data/myscan_00023.scan.json " \
        + " -d /user/data/myscan_00023.origdatablock.json " \
        + " -a /user/data/myscan_00023.attachment.json  \n" \
        + " \n" \
        + "       nxsfileinfo groupmetadata " \
        + " -m /user/data/myscan_00023.scan.json " \
        + " -d /user/data/myscan_00023.origdatablock.json " \
        + " -c /home/user/group_config.txt " \
        + " \n" \
        + "\n"

    listtype = ["List", "L", "l", "list"]
    dicttype = ["Dict", "D", "d", "dict"]
    rangetype = ["Range", "R", "r", "rangle"]
    minmaxtype = ["MinMax", "M", "m", "minmax"]
    mintype = ["Min", "min"]
    maxtype = ["Max", "max"]
    uniquelisttype = ["UniqueList", "U", "u", "uniquelist"]
    singlelisttype = ["SingleList", "S", "s", "singlelist"]
    endpointstype = ["Endpoints",  "endpoints", "E", "e"]
    firstlasttype = ["FirstLast",  "firstlast"]
    lasttype = ["Last", "last", "l", "L"]
    firsttype = ["First", "first", "f", "F"]
    # avaragetype = ["Average", "A", "a", "average"]

    def create(self):
        """ creates parser

        """
        # self._parser.add_argument(
        #     "-w", "--owner-group",
        #     default="", dest="ownergroup",
        #     help="owner group name. Default is {beamtimeid}-dmgt")
        # self._parser.add_argument(
        #     "-c", "--access-groups",
        #     default=None, dest="accessgroups",
        #     help="access group names separated by commas. "
        #     "Default is {beamtimeId}-dmgt,
        #       {beamtimeid}-clbt,{beamtimeId}-part,"
        #     "{beamline}dmgt,{beamline}staff")
        self._parser.add_argument(
            "-p", "--pid", dest="pid",
            help=("dataset pid"))
        self._parser.add_argument(
            "-i", "--beamtimeid", dest="beamtimeid",
            help=("beamtime id"))
        # self._parser.add_argument(
        #     "-u", "--pid-with-uuid", action="store_true",
        #     default=False, dest="puuid",
        #     help=("generate pid with uuid"))
        # self._parser.add_argument(
        #     "-d", "--pid-without-filename", action="store_true",
        #     default=False, dest="pfname",
        #     help=("generate pid without file name"))
        self._parser.add_argument(
            "-s", "--skip-group-datablock", action="store_true",
            default=False, dest="skipgroupdatablock",
            help=("skip group datablock"))
        self._parser.add_argument(
            "-w", "--allow-duplication", action="store_true",
            default=False, dest="nounique",
            help=("allow to merge metadata with duplicated pid"))
        self._parser.add_argument(
            "-q", "--raw", action="store_true",
            default=False, dest="raw",
            help="raw dataset type")
        self._parser.add_argument(
            "-f", "--write-files", action="store_true",
            default=False, dest="writefiles",
            help=("write output to files"))
        self._parser.add_argument(
            "-k", "--scicat-version",
            default=4, dest="scicatversion",
            help="major scicat version metadata")
        self._parser.add_argument(
            "-x", "--chmod", dest="chmod",
            help=("json metadata file mod bits, e.g. 0o662"))
        self._parser.add_argument(
            "-g --group-map", dest="groupmap",
            help=("json or yaml map of {output: input} "
                  "or [[output, input],]  or a text file list "
                  " to re-arrange metadata"))
        self._parser.add_argument(
            'group', metavar='group', type=str, nargs="*",
            help='group name')
        self._parser.add_argument(
            "-e", "--group-map-error", action="store_true",
            default=False, dest="groupmaperror",
            help=("Raise an error when the group map file does not exist"))

    def postauto(self):
        """ parser creator after autocomplete run """
        # self._parser.add_argument(
        #     "-b", "--beamtime-meta", dest="beamtimemeta",
        #     help=("beamtime metadata file"))
        # self._parser.add_argument(
        #     "-s", "--scientific-meta", dest="scientificmeta",
        #     help=("scientific metadata file"))
        self._parser.add_argument(
            "-r", "--group-map-file", dest="groupmapfile",
            help=("json or yaml file containing the copy map, "
                  "see also --group-map"))
        self._parser.add_argument(
            "-m", "--metadata", dest="metadatafile",
            help=("json metadata file"))
        self._parser.add_argument(
            "-d", "--origdatablock", dest="origdatablockfile",
            help=("json origmetadata file"))
        self._parser.add_argument(
            "-a", "--attachment", dest="attachmentfile",
            help=("json attachment file"))
        self._parser.add_argument(
            "-o", "--output", dest="output",
            help=("output scicat group metadata file"))
        self._parser.add_argument(
            "-l", "--datablock-output", dest="dboutput",
            help=("output scicat group datablocks list file"))
        self._parser.add_argument(
            "-t", "--attachment-output", dest="atoutput",
            help=("output scicat group attachments list file"))
        # self._parser.add_argument(
        #     "-r", "--relative-path", dest="relpath",
        #     help=("relative path to the scan files"))

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        self.show(options)

    @classmethod
    def _cure(cls, result):
        if 'creationTime' not in result:
            result['creationTime'] = isoDate(filewriter.FTFile.currenttime())
        else:
            result['creationTime'] = isoDate(result['creationTime'])
        if 'endTime' in result:
            result['endTime'] = isoDate(result['endTime'])

        if 'type' not in result:
            result['type'] = 'raw'
        if 'creationLocation' not in result:
            result['creationLocation'] = "/DESY/PETRA III"
        if 'ownerGroup' not in result:
            result['ownerGroup'] = "ingestor"
        return result

    @classmethod
    def _group_metadata(cls, grfile, scfile, clist, options):
        """ group scan metadata

        :param grfile: grouped metadata file
        :type grfile: :obj:`str`
        :param scfile: scan metadata file
        :type scfile: :obj:`str`
        :param clist: copy list to overwrite metadata
        :type clist: :obj:`list` < [:obj:`str`, :obj:`str`] >
        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: grouped metadata
        :rtype: :obj:`dct` <:obj:`str`, `any`>
        """
        # print("GROUP", grfile, scfile)
        try:
            with open(scfile, "r") as fl:
                sfl = fl.read()
            ds = json.loads(sfl)
            if not isinstance(ds, dict):
                ds = {}
        except Exception as e:
            print("WARNING: %s" % str(e))
            ds = {}
        try:
            with open(grfile, "r") as fl:
                sfl = fl.read()
            metadata = json.loads(sfl)
            if not isinstance(ds, dict):
                metadata = {}
        except Exception as e:
            print("WARNING: %s" % str(e))
            metadata = {}

        metadata = cls._update_metadata(metadata, ds, clist,
                                        options.nounique)
        return metadata

    @classmethod
    def _update_metadata(cls, gr, ds, cplist, nounique=False):
        """ update and group scan metadata

        :param gr: group metadata
        :type gr: :obj:`dict`
        :param ds: scan metadata
        :type ds: :obj:`dict`
        :param clist: copy list to overwrite metadata
        :type clist: :obj:`list` < [:obj:`str`, :obj:`str`] >
        :returns: grouped metadata
        :rtype: :obj:`dct` <:obj:`str`, `any`>
        """
        first = True
        for line in cplist:
            if line and len(line) > 1 and line[0] and line[1] and \
               isinstance(line[0], basestring) and \
               isinstance(line[1], basestring) and \
               not line[0].startswith(line[1] + "."):
                ts = line[0]
                vs = line[1]
                vls = vs.split(".")
                md = ds
                for vl in vls:
                    if vl in md:
                        md = md[vl]
                    else:
                        break
                else:
                    tgs = ts.split(".")
                    td = gr
                    parent = None
                    for tg in tgs:
                        parent = td
                        if tg in td:
                            td = td[tg]
                        else:
                            td[tg] = {}
                            td = td[tg]
                    if not nounique and first and \
                       tg == 'inputDatasets' and \
                       isinstance(td, list) and md in td:
                        return gr
                    tgtype = line[2] if len(line) > 2 else None
                    cls._merge_meta(parent, tg, md, tgtype)
            first = False
        return gr

    @classmethod
    def _merge_string(cls, parent, key, md, tgtype=None):
        """ update and group scan metadata

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param tgtype: target type
        :type tgtype: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if tgtype in cls.listtype or tgtype in cls.uniquelisttype \
                or tgtype in cls.singlelisttype:
            if not isinstance(tg, list):
                if tg:
                    parent[key] = [tg]
                else:
                    parent[key] = []
        if tgtype in cls.dicttype:
            if not isinstance(tg, dict):
                parent[key] = {}
            sz = str(len(parent[key]))
            parent[key][sz] = md
        elif tgtype in cls.lasttype:
            parent[key] = md
        elif tgtype in cls.firsttype:
            if tg in [None, [], {}]:
                parent[key] = md
        elif tgtype in cls.firstlasttype:
            if not isinstance(tg, dict):
                parent[key] = {}
            parent[key]["last"] = md
            if "first" not in parent[key].keys():
                parent[key]["first"] = md
        elif tgtype in cls.endpointstype:
            if not isinstance(tg, list) or len(parent[key]) != 2:
                parent[key] = [md, md]
            else:
                parent[key][1] = md
        elif key in parent and isinstance(parent[key], list):
            if (tgtype not in cls.uniquelisttype and
                tgtype not in cls.singlelisttype) or \
                    md not in parent[key]:
                parent[key].append(md)
        elif not tg:
            parent[key] = md
        elif tg != md:
            parent[key] = [tg, md]

    @classmethod
    def _list_depth(cls, lst):
        """calculate list depth

        :param lst: target type
        :type lst: :obj:`list`
        :returns: list depth
        :rtype: :obj:`int`
        """
        if not isinstance(lst, list):
            return 0
        elif not len(lst):
            return 1
        else:
            return cls._list_depth(lst[0]) + 1

    @classmethod
    def _merge_range_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {}
        tg = parent[key]
        if "value" not in tg:
            tg["value"] = []
        if "unit" not in tg:
            tg["unit"] = unit
        try:
            mmin = min(md)
        except Exception:
            mmin = md
        try:
            mmax = max(md)
        except Exception:
            mmax = md
        if not isinstance(tg["value"], list) or len(tg["value"]) != 2:
            tg["value"] = [mmin, mmax]
        try:
            if tg["value"][0] > mmin:
                tg["value"][0] = mmin
            if tg["value"][1] < mmax:
                tg["value"][1] = mmax
        except Exception:
            tg["value"] = [mmin, mmax]
        return

    @classmethod
    def _merge_minmax_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {}
        tg = parent[key]
        try:
            mmin = min(md)
        except Exception:
            mmin = md
        try:
            mmax = max(md)
        except Exception:
            mmax = md
        if not isinstance(tg, dict):
            parent[key] = {"min": {"value": mmin, "unit": unit},
                           "max": {"value": mmax, "unit": unit}}
        if "min" not in parent[key]:
            parent[key]["min"] = {"value": mmin, "unit": unit}
        if "max" not in parent[key]:
            parent[key]["max"] = {"value": mmax, "unit": unit}

        try:
            if parent[key]["min"]["value"] > mmin:
                parent[key]["min"]["value"] = mmin
            if parent[key]["max"]["value"] < mmax:
                parent[key]["max"]["value"] = mmax
        except Exception:
            parent[key] = {"min": {"value": mmin, "unit": unit},
                           "max": {"value": mmax, "unit": unit}}
        return

    @classmethod
    def _merge_max_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {}
        tg = parent[key]
        try:
            mmax = max(md)
        except Exception:
            mmax = md
        if not isinstance(tg, dict):
            parent[key] = {"value": mmax, "unit": unit}
        if "value" not in parent[key]:
            parent[key]["value"] = mmax
            parent[key]["unit"] = unit

        try:
            if parent[key]["value"] < mmax:
                parent[key]["value"] = mmax
        except Exception:
            parent[key] = {"value": mmax, "unit": unit}
        return

    @classmethod
    def _merge_min_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {}
        tg = parent[key]
        try:
            mmin = min(md)
        except Exception:
            mmin = md
        if not isinstance(tg, dict):
            parent[key] = {"value": mmin, "unit": unit}
        if "value" not in parent[key]:
            parent[key]["value"] = mmin
            parent[key]["unit"] = unit

        try:
            if parent[key]["value"] > mmin:
                parent[key]["value"] = mmin
        except Exception:
            parent[key] = {"value": mmin, "unit": unit}
        return

    @classmethod
    def _merge_list_list(cls, parent, key, md, unit, tgtype):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not unit:
            if not isinstance(tg, list):
                if tg is not None and tg != {} and tg != []:
                    parent[key] = [tg]
                else:
                    parent[key] = []
            elif tgtype in cls.uniquelisttype and \
                    len(tg) > 0 and \
                    cls._list_depth(tg) <= cls._list_depth(md) \
                    and md != parent[key]:
                parent[key] = [tg]

            if tgtype in cls.singlelisttype:
                for mm in md:
                    if mm not in parent[key]:
                        parent[key].append(mm)
            elif tgtype not in cls.uniquelisttype or \
                    (md not in parent[key] and md != parent[key]):
                if tgtype in cls.uniquelisttype and not parent[key]:
                    parent[key] = md
                else:
                    parent[key].append(md)
        else:
            if not isinstance(tg, dict):
                parent[key] = {}
            tg = parent[key]
            if "value" not in tg:
                tg["value"] = 0
            if "unit" not in tg:
                tg["unit"] = unit
            if not isinstance(tg["value"], list):
                tg["value"] = []
            elif tgtype in cls.uniquelisttype and \
                    len(tg["value"]) > 0 and \
                    cls._list_depth(tg["value"]) <= cls._list_depth(md) \
                    and md != tg["value"]:
                parent[key]["value"] = [tg["value"]]
                tg = parent[key]

            if tgtype not in cls.uniquelisttype or \
               (md not in tg["value"] and md != tg["value"]):
                if tgtype in cls.uniquelisttype \
                   and not parent[key]["value"]:
                    tg["value"] = md
                else:
                    tg["value"].append(md)

    @classmethod
    def _merge_dict_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not unit:
            if not isinstance(tg, dict):
                if tg is not None and tg != {} and tg != []:
                    parent[key] = {"0": tg}
                else:
                    parent[key] = {}
            sz = str(len(parent[key]))
            parent[key][sz] = md
        else:
            if not isinstance(tg, dict):
                parent[key] = {}
            sz = str(len(parent[key]))
            parent[key][sz] = {"value": md, "unit": unit}

    @classmethod
    def _merge_average_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if isinstance(md[0], basestring):
            if isinstance(tg, list):
                parent[key].extend(
                    [mi for mi in md if mi not in tg])
            elif not tg:
                parent[key] = md
        elif (isinstance(md[0], float) or isinstance(md[0], int)) \
                and len(md) < 4:
            if isinstance(tg, list):
                if md not in parent[key]:
                    parent[key].append(md)
            elif not tg:
                parent[key] = [md]
        else:
            for mi in md:
                if not isinstance(mi, float) and \
                   not isinstance(mi, int):
                    break
            else:
                value = md
                tg = None
                if key in parent.keys():
                    tg = parent[key]
                if not isinstance(tg, dict):
                    parent[key] = {}
                    tg = parent[key]
                if "value" not in tg:
                    tg["value"] = 0
                if "unit" not in tg:
                    tg["unit"] = unit
                if "min" not in tg:
                    tg["min"] = min(value)
                if "max" not in tg:
                    tg["max"] = max(value)
                if "std" not in tg:
                    tg["std"] = 0.0
                if "counts" not in tg:
                    tg["counts"] = 0
                ov = tg["value"]
                ocnts = tg["counts"]
                ostd = tg["std"]
                if ostd is not None:
                    os2 = ostd * ostd
                nn = len(md)
                ncnts = ocnts + nn
                tg["counts"] = ncnts
                if tg["unit"] == unit and tg["value"] is not None:
                    tg["value"] = \
                        float((ov * ocnts) + sum(value)) / ncnts
                    minv = min(value)
                    if tg["min"] > minv:
                        tg["min"] = minv
                    maxv = max(value)
                    if tg["max"] < maxv:
                        tg["max"] = maxv
                if ncnts > 1 and tg["std"] is not None:
                    if (ocnts == 1 or nn == 1):
                        tg["std"] = float(
                            np.std([ov] + value, ddof=1))
                    elif ostd == 0.0:
                        tg["std"] = float(
                            np.std(value, ddof=1))
                    elif ocnts > 1 and nn > 1:
                        nvar = float(
                            np.var(value, ddof=1))
                        tg["std"] = \
                            math.sqrt(
                                ((ocnts - 1) * os2 + (nn - 1) * nvar)
                                / (ncnts - 2))
                if isinstance(tg["std"], float) and \
                   (math.isinf(tg["std"]) or math.isnan(tg["std"])):
                    tg["std"] = None
                if isinstance(tg["value"], float) and \
                   (math.isinf(tg["value"]) or math.isnan(tg["value"])):
                    tg["value"] = None

    @classmethod
    def _merge_first_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {}
        tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {"value": md, "unit": unit}
        if "value" not in parent[key]:
            parent[key]["value"] = md
            parent[key]["unit"] = unit
        return

    @classmethod
    def _merge_last_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {}
        tg = parent[key]
        parent[key] = {"value": md, "unit": unit}
        return

    @classmethod
    def _merge_firstlast_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {}

        if not isinstance(parent[key], dict):
            parent[key] = {"first": {"value": md, "unit": unit},
                           "last": {"value": md, "unit": unit}}
        if "first" not in parent[key]:
            parent[key]["first"] = {"value": md, "unit": unit}
        parent[key]["last"] = {"value": md, "unit": unit}
        return

    @classmethod
    def _merge_endpoints_list(cls, parent, key, md, unit):
        """ merge list

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {}

        if not isinstance(parent[key], dict):
            parent[key] = {"value": [md, md], "unit": unit}
        if "value" not in parent[key] or len(parent[key]["value"]) != 2:
            parent[key] = {"value": [md, md], "unit": unit}
        parent[key]["value"][1] = md
        return

    @classmethod
    def _merge_list(cls, parent, key, md, unit, tgtype=None):
        """ update and group scan metadata

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        :param tgtype: target type
        :type tgtype: :obj:`str`
        """
        if tgtype in cls.rangetype and md and \
           (isinstance(md[0], float) or isinstance(md[0], int)):
            return cls._merge_range_list(parent, key, md, unit)
        if tgtype in cls.minmaxtype and md and \
           (isinstance(md[0], float) or isinstance(md[0], int)):
            return cls._merge_minmax_list(parent, key, md, unit)
        if tgtype in cls.maxtype and md and \
           (isinstance(md[0], float) or isinstance(md[0], int)):
            return cls._merge_max_list(parent, key, md, unit)
        if tgtype in cls.mintype and md and \
           (isinstance(md[0], float) or isinstance(md[0], int)):
            return cls._merge_min_list(parent, key, md, unit)
        if tgtype in cls.firsttype:
            return cls._merge_first_list(parent, key, md, unit)
        if tgtype in cls.lasttype:
            return cls._merge_last_list(parent, key, md, unit)
        if tgtype in cls.firstlasttype:
            return cls._merge_firstlast_list(parent, key, md, unit)
        if tgtype in cls.endpointstype:
            return cls._merge_endpoints_list(parent, key, md, unit)
        if tgtype in cls.listtype or tgtype in cls.uniquelisttype \
                or tgtype in cls.singlelisttype:
            return cls._merge_list_list(parent, key, md, unit, tgtype)
        elif tgtype in cls.dicttype:
            return cls._merge_dict_list(parent, key, md, unit)
        elif md:
            return cls._merge_average_list(parent, key, md, unit)

    @classmethod
    def _merge_range_number(cls, parent, key, md, unit):
        """ merge metadata number to range type

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """

        tg = parent[key]
        if "value" not in tg:
            tg["value"] = 0
        if "unit" not in tg:
            tg["unit"] = unit
        if not isinstance(tg["value"], list) or len(tg["value"]) != 2:
            tg["value"] = [md, md]
        try:
            if tg["value"][0] > md:
                tg["value"][0] = md
            if tg["value"][1] < md:
                tg["value"][1] = md
        except Exception:
            tg["value"] = [md, md]
        return

    @classmethod
    def _merge_min_number(cls, parent, key, md, unit):
        """ merge metadata number to min type

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        if not isinstance(parent[key], dict):
            parent[key] = {"value": md, "unit": unit}
        if "value" not in parent[key]:
            parent[key] = {"value": md, "unit": unit}
        try:
            if parent[key]["value"] > md:
                parent[key]["value"] = md
        except Exception:
            parent[key] = {"value": md, "unit": unit}
        return

    @classmethod
    def _merge_max_number(cls, parent, key, md, unit):
        """ merge metadata number to min type

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """

        if not isinstance(parent[key], dict):
            parent[key] = {"value": md, "unit": unit}
        if "value" not in parent[key]:
            parent[key] = {"value": md, "unit": unit}
        try:
            if parent[key]["value"] < md:
                parent[key]["value"] = md
        except Exception:
            parent[key] = {"value": md, "unit": unit}
        return

    @classmethod
    def _merge_minmax_number(cls, parent, key, md, unit):
        """ merge metadata number to minmax type

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        if not isinstance(parent[key], dict):
            parent[key] = {"min": {"value": md, "unit": unit},
                           "max": {"value": md, "unit": unit}}
        if "min" not in parent[key]:
            parent[key]["min"] = {"value": md, "unit": unit}
        if "max" not in parent[key]:
            parent[key]["max"] = {"value": md, "unit": unit}
        try:
            if parent[key]["min"]["value"] > md:
                parent[key]["min"]["value"] = md
            if parent[key]["max"]["value"] < md:
                parent[key]["max"]["value"] = md
        except Exception:
            parent[key] = {"min": {"value": md, "unit": unit},
                           "max": {"value": md, "unit": unit}}
        return

    @classmethod
    def _merge_list_number(cls, parent, key, md, unit):
        """ merge metadata number to minmax type

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        tg = parent[key]

        if "value" not in tg:
            tg["value"] = 0
        if "unit" not in tg:
            tg["unit"] = unit
        if not isinstance(tg["value"], list):
            tg["value"] = []
        tg["value"].append(md)
        return

    @classmethod
    def _merge_dict_number(cls, parent, key, md, unit):
        """ merge metadata number to dict type

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        if not isinstance(parent[key], dict):
            parent[key] = {}
        sz = str(len(parent[key]))
        parent[key][sz] = {"value": md, "unit": unit}
        return

    @classmethod
    def _merge_first_number(cls, parent, key, md, unit):
        """ merge metadata number to first type

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        if not isinstance(parent[key], dict):
            parent[key] = {"value": md, "unit": unit}
        if "value" not in parent[key]:
            parent[key] = {"value": md, "unit": unit}
        return

    @classmethod
    def _merge_last_number(cls, parent, key, md, unit):
        """ merge metadata number to last type

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        parent[key] = {"value": md, "unit": unit}
        return

    @classmethod
    def _merge_firstlast_number(cls, parent, key, md, unit):
        """ merge metadata number to firstlast type
i
        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """

        if not isinstance(parent[key], dict):
            parent[key] = {"first": {"value": md, "unit": unit},
                           "last": {"value": md, "unit": unit}}
        if "first" not in parent[key]:
            parent[key]["first"] = {"value": md, "unit": unit}
        parent[key]["last"] = {"value": md, "unit": unit}
        return

    @classmethod
    def _merge_endpoints_number(cls, parent, key, md, unit):
        """ merge metadata number to endpoints type
i
        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """

        if not isinstance(parent[key], dict):
            parent[key] = {"value": [md, md], "unit": unit}
        if "value" not in parent[key] or len(parent[key]["value"]) != 2:
            parent[key] = {"value": [md, md], "unit": unit}
        parent[key]["value"][1] = md
        return

    @classmethod
    def _merge_average_number(cls, parent, key, md, unit):
        """ merge metadata number to dict type

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        """
        value = md
        tg = parent[key]

        if not isinstance(tg, dict):
            parent[key] = {}
        if "value" not in tg:
            tg["value"] = 0
        if "unit" not in tg:
            tg["unit"] = unit
        if "min" not in tg:
            tg["min"] = value
        if "max" not in tg:
            tg["max"] = value
        if "std" not in tg:
            tg["std"] = 0.0
        if "counts" not in tg:
            tg["counts"] = 0
        ov = tg["value"]
        ocnts = tg["counts"]
        ostd = tg["std"]
        if ostd is not None:
            os2 = ostd * ostd

        ncnts = ocnts + 1
        if tg["unit"] == unit and tg["value"] is not None:
            tg["value"] = float((ov * ocnts) + value)/(ncnts)
            if tg["min"] > value:
                tg["min"] = value
            if tg["max"] < value:
                tg["max"] = value
            tg["counts"] += 1
            if ncnts == 2 and tg["value"] is not None:
                ns2 = float(
                    (value - tg["value"]) * (value - tg["value"])
                    + (ov - tg["value"]) * (ov - tg["value"]))
                tg["std"] = math.sqrt(ns2)
            elif ncnts > 2 and tg["value"] is not None and ostd is not None:
                # ns2 = float(
                #     (ncnts - 2) * os2
                #     +x (value - tg["value"]) * (value - ov)
                # ) \ (ncnts - 1)
                ns2 = float(
                    (ncnts - 2) * os2
                    + (value - tg["value"]) * (value - ov)
                ) / (ncnts - 1)
                tg["std"] = math.sqrt(ns2)
            if isinstance(tg["std"], float) and \
               (math.isinf(tg["std"]) or math.isnan(tg["std"])):
                tg["std"] = None
            if isinstance(tg["value"], float) and \
               (math.isinf(tg["value"]) or math.isnan(tg["value"])):
                tg["value"] = None

    @classmethod
    def _merge_number(cls, parent, key, md, unit, tgtype=None):
        """ update and group scan metadata

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param unit: physical unit
        :type unit: :obj:`str`
        :param tgtype: target type
        :type tgtype: :obj:`str`
        """
        tg = None
        if key in parent.keys():
            tg = parent[key]
        if not isinstance(tg, dict):
            parent[key] = {}

        if tgtype in cls.rangetype:
            return cls._merge_range_number(parent, key, md, unit)
        if tgtype in cls.mintype:
            return cls._merge_min_number(parent, key, md, unit)
        if tgtype in cls.maxtype:
            return cls._merge_max_number(parent, key, md, unit)
        if tgtype in cls.minmaxtype:
            return cls._merge_minmax_number(parent, key, md, unit)
        if tgtype in cls.listtype:
            return cls._merge_list_number(parent, key, md, unit)
        if tgtype in cls.dicttype:
            return cls._merge_dict_number(parent, key, md, unit)
        if tgtype in cls.firsttype:
            return cls._merge_first_number(parent, key, md, unit)
        if tgtype in cls.lasttype:
            return cls._merge_last_number(parent, key, md, unit)
        if tgtype in cls.firstlasttype:
            return cls._merge_firstlast_number(parent, key, md, unit)
        if tgtype in cls.endpointstype:
            return cls._merge_endpoints_number(parent, key, md, unit)
        return cls._merge_average_number(parent, key, md, unit)

    @classmethod
    def _merge_meta(cls, parent, key, md, tgtype=None):
        """ update and group scan metadata

        :param parent: node metadata
        :type parent: :obj:`dict`
        :param key: metadata key
        :type key: :obj:`str`
        :param md: new metadata
        :type md: :obj:`str` or :obj:`dict`
        :param tgtype: target type
        :type tgtype: :obj:`str`
        """
        if isinstance(md, basestring):
            cls._merge_string(parent, key, md, tgtype)
        unit = ""
        if isinstance(md, dict):
            if "unit" in md:
                unit = md["unit"]
            if "value" in md and not isinstance(md["value"], dict):
                md = md["value"]
            else:
                if isinstance(md, dict):
                    for ky in md.keys():
                        parent[key]
                        if not isinstance(parent[key], dict):
                            if parent[key] is not None:
                                vl = parent[key]
                                parent[key] = {key: vl}
                            else:
                                parent[key] = {}
                        tg = parent[key]
                        cls._merge_meta(tg, ky, md[ky], tgtype)
                md = None

        if isinstance(md, list):
            cls._merge_list(parent, key, md, unit, tgtype)
        elif isinstance(md, float) or isinstance(md, int):
            cls._merge_number(parent, key, md, unit, tgtype)

    @classmethod
    def _create_metadata(cls, scfile, clist, options):
        """ group scan metadata

        :param scfile: scan metadata file
        :type scfile: :obj:`str`
        :param clist: copy list to overwrite metadata
        :type clist: :obj:`list` < [:obj:`str`, :obj:`str`] >
        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: [grouped metadata,
                   grouped origdatablocks,
                   grouped attachments]
        :rtype: [:obj:`str`,:obj:`str`, :obj:`str`]
        """

        cpmap = {
            "accessGroups": "accessGroups",
            "creationTime": "creationTime",
            "contactEmail": "contactEmail",
            "sourceFolderHost": "sourceFolderHost",
            "description": "description",
            "isPublished": "isPublished",
            "owner": "owner",
            "ownerEmail": "ownerEmail",
            "ownerGroup": "ownerGroup",
            "investigator": "principalInvestigator",
            "sourceFolder": "sourceFolder",
            "techniques": "techniques",
            "scientificMetadata.instrumentId": "instrumentId",
            "scientificMetadata.creationLocation": "creationLocation",
            "scientificMetadata.proposalId": "proposalId",
            "scientificMetadata.DOOR_proposalId":
            "scientificMetadata.DOOR_proposalId",
            "scientificMetadata.beamtimeId":
            "scientificMetadata.beamtimeId",
        }

        metadata = {
            "type": "derived",
            "inputDatasets": [],
            "keywords": ["measurement"],
            "usedSoftware": "https://github.com/nexdatas/nxstools",
            "jobParameters": {"command": "nxsfileinfo groupmetadata"},
        }
        rawmetadata = {
            "type": "raw",
            "scientificMetadata": {
                "inputDatasets": [],
                "usedSoftware": "https://github.com/nexdatas/nxstools",
                "jobParameters": {"command": "nxsfileinfo groupmetadata"}
            },
            "keywords": ["measurement"],
        }
        if options.raw:
            metadata = rawmetadata
        try:
            with open(scfile, "r") as fl:
                sfl = fl.read()
            ds = json.loads(sfl)
            if not isinstance(ds, dict):
                ds = {}
        except Exception as e:
            print("WARNING: %s" % str(e))
            ds = {}

        beamtimeid = "00000000"
        group = ""
        if "pid" in ds and ds["pid"]:
            spid = ds["pid"].split("/")
        else:
            spid = []
        if options.group and options.group[0]:
            group = options.group[0]
        if options.beamtimeid:
            beamtimeid = options.beamtimeid
        else:
            if len(spid) > 1:
                beamtimeid = spid[-2]
            elif len(spid):
                beamtimeid = spid[0]
        if options.pid:
            metadata["pid"] = str(options.pid)
        else:
            if len(spid) > 1:
                spid[-1] = beamtimeid
                spid[-2] = group
                metadata["pid"] = str("/".join(spid))
            else:
                metadata["pid"] = str(
                    "%s/%s" % (group, beamtimeid))
        if group:
            metadata["keywords"].append(group)
            if "datasetName" not in metadata:
                metadata["datasetName"] = group

        for ts, vs in cpmap.items():
            if options.raw:
                ts = vs
            if ts and vs and isinstance(ts, basestring) \
               and isinstance(vs, basestring) \
               and not ts.startswith(vs + "."):
                vls = vs.split(".")
                md = ds
                for vl in vls:
                    if vl in md:
                        md = md[vl]
                    else:
                        break
                else:
                    tgs = ts.split(".")
                    td = metadata
                    parent = None
                    for tg in tgs:
                        parent = td
                        if tg in td:
                            td = td[tg]
                        else:
                            td[tg] = {}
                            td = td[tg]
                    parent[tg] = md

        metadata = cls._update_metadata(metadata, ds, clist)
        return metadata

    @classmethod
    def groupmetadata(cls, options):
        """ group scan metadata

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: [grouped metadata,
                   grouped origdatablocks,
                   grouped attachments]
        :rtype: [:obj:`str`,:obj:`str`, :obj:`str`]
        """
        result = None
        dresult = []
        aresult = []

        imfile = options.metadatafile
        omfile = None
        metadir = os.getcwd()
        if imfile and os.path.isfile(imfile):
            if options.output:
                omfile = options.output
            elif options.group and options.group[0]:
                if imfile:
                    metadir, _ = os.path.split(os.path.abspath(imfile))
                    if not os.path.isdir(metadir):
                        os.makedirs(metadir, exist_ok=True)
                omfile = os.path.join(
                    metadir, "%s.scan.json" % options.group[0])
                if options.writefiles:
                    options.output = omfile

        idfile = options.origdatablockfile
        odfile = None
        if options.dboutput:
            odfile = options.dboutput
        elif options.group and options.group[0]:
            if imfile and os.path.isfile(imfile):
                metadir, _ = os.path.split(os.path.abspath(imfile))
            elif idfile:
                metadir, _ = os.path.split(os.path.abspath(idfile))
            elif omfile:
                metadir, _ = os.path.split(os.path.abspath(omfile))
            if metadir:
                odfile = os.path.join(
                    metadir, "%s.origdatablock.json" % options.group[0])
                if options.writefiles:
                    options.dboutput = odfile

        iafile = options.attachmentfile
        oafile = None
        if options.atoutput:
            oafile = options.atoutput
        elif options.group and options.group[0]:
            if imfile and os.path.isfile(imfile):
                metadir, _ = os.path.split(os.path.abspath(imfile))
            elif iafile:
                metadir, _ = os.path.split(os.path.abspath(iafile))
            elif omfile:
                metadir, _ = os.path.split(os.path.abspath(omfile))
            if metadir:
                oafile = os.path.join(
                    metadir, "%s.attachment.json" % options.group[0])
                if options.writefiles:
                    options.atoutput = oafile

        usergroupmap = {}
        usergrouplist = []
        if options.raw:
            grouplist = [["scientificMetadata.inputDatasets", "pid"]]
        else:
            grouplist = [["inputDatasets", "pid"]]

        if hasattr(options, "groupmap") and options.groupmap:
            dct = yaml.safe_load(options.groupmap.strip())
            if dct and isinstance(dct, dict):
                usergroupmap.update(dct)
            elif dct:
                if isinstance(dct, basestring):
                    dct = getlist(options.groupmap.strip())
                if isinstance(dct, list):
                    for line in dct:
                        if isinstance(line, list):
                            if len(line) > 2:
                                usergrouplist.append(line[:3])
                            else:
                                usergrouplist.append(line[:2])

        if hasattr(options, "groupmapfile") and options.groupmapfile:
            if os.path.isfile(options.groupmapfile):
                with open(options.groupmapfile, "r") as fl:
                    jstr = fl.read()
                    # print(jstr)
                    try:
                        dct = yaml.safe_load(jstr.strip())
                    except Exception:
                        if jstr:
                            nan = float('nan')    # noqa: F841
                            try:
                                dct = eval(jstr.strip())
                            except Exception:
                                dct = " "
                            # mdflatten(dstr, [], dct)
                    if dct and isinstance(dct, dict):
                        usergroupmap.update(dct)
                    elif dct:
                        if isinstance(dct, basestring):
                            dct = getlist(jstr.strip())
                        if isinstance(dct, list):
                            for line in dct:
                                if isinstance(line, list):
                                    if len(line) > 2:
                                        usergrouplist.append(line[:3])
                                    else:
                                        usergrouplist.append(line[:2])
            elif hasattr(options, "groupmaperror") and options.groupmaperror:
                raise Exception("Group-map file '%s' does not exist"
                                % options.groupmapfile)

        grouplist.extend(usergrouplist)
        for ky, vl in usergroupmap.items():
            if vl:
                grouplist.append([ky, vl])
        if omfile:
            if os.path.isfile(omfile):
                result = cls._group_metadata(
                    omfile, imfile, grouplist, options)
            else:
                result = cls._create_metadata(
                    imfile, grouplist, options)

        ogroupfilename = ""
        if odfile:
            odir, ofile = os.path.split(odfile)
            ogroupfilename = os.path.join(odir, "_" + ofile)
        if odfile and os.path.isfile(odfile):
            with open(odfile, "r") as fl:
                jstr = fl.read()
                try:
                    dresult = json.loads(jstr)
                    if not isinstance(dresult, list):
                        shutil.copy(odfile, ogroupfilename)
                        dresult = [ogroupfilename]
                except Exception:
                    dresult = []
        if idfile and os.path.isfile(idfile) and idfile not in dresult:
            dresult.append(idfile)
        if not options.skipgroupdatablock and os.path.isfile(ogroupfilename) \
           and ogroupfilename not in dresult:
            dresult.insert(0, ogroupfilename)

        agroupfilename = ""
        if oafile:
            adir, afile = os.path.split(oafile)
            agroupfilename = os.path.join(adir, "_" + afile)
        if oafile and os.path.isfile(oafile):
            with open(oafile, "r") as fl:
                jstr = fl.read()
                try:
                    aresult = json.loads(jstr)
                    if not isinstance(aresult, list):
                        shutil.copy(oafile, agroupfilename)
                        aresult = [agroupfilename]
                except Exception:
                    aresult = []
        if iafile and os.path.isfile(iafile) and iafile not in aresult:
            aresult.append(iafile)
        if not options.skipgroupdatablock and os.path.isfile(agroupfilename) \
           and agroupfilename not in aresult:
            aresult.insert(0, agroupfilename)

        jsnresult = None
        if result is not None:
            jsnresult = json.dumps(
                result, sort_keys=True, indent=4, cls=numpyEncoderNull)
        return [jsnresult, json.dumps(dresult), json.dumps(aresult)]

    def show(self, options):
        """ the main function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        try:
            metadata, datablocks, attachments = self.groupmetadata(options)
            if metadata:
                if options.output:
                    fdir, fn = os.path.split(os.path.abspath(options.output))
                    if not os.path.isdir(fdir):
                        os.makedirs(fdir, exist_ok=True)
                    chmod = None
                    try:
                        chmod = int(options.chmod, 8)
                    except Exception:
                        options.chmod = None

                    if options.chmod:
                        oldmask = os.umask(0)

                        def opener(path, flags):
                            return os.open(path, flags, chmod)

                        try:
                            with open(options.output,
                                      "w", opener=opener) as fl:
                                fl.write(metadata)
                        except Exception:
                            with open(options.output, "w") as fl:
                                fl.write(metadata)
                            os.chmod(options.output, chmod)
                        os.umask(oldmask)
                    else:
                        with open(options.output, "w") as fl:
                            fl.write(metadata)
                else:
                    print(metadata)
                if options.dboutput:
                    chmod = None
                    try:
                        chmod = int(options.chmod, 8)
                    except Exception:
                        options.chmod = None

                    if options.chmod:
                        oldmask = os.umask(0)

                        def opener(path, flags):
                            return os.open(path, flags, chmod)

                        try:
                            with open(options.dboutput,
                                      "w", opener=opener) as fl:
                                fl.write(datablocks)
                        except Exception:
                            with open(options.dboutput, "w") as fl:
                                fl.write(datablocks)
                            os.chmod(options.dboutput, chmod)
                        os.umask(oldmask)
                    else:
                        with open(options.dboutput, "w") as fl:
                            fl.write(datablocks)
                else:
                    print(datablocks)
                if options.atoutput:
                    chmod = None
                    try:
                        chmod = int(options.chmod, 8)
                    except Exception:
                        options.chmod = None

                    if options.chmod:
                        oldmask = os.umask(0)

                        def opener(path, flags):
                            return os.open(path, flags, chmod)

                        try:
                            with open(options.atoutput,
                                      "w", opener=opener) as fl:
                                fl.write(attachments)
                        except Exception:
                            with open(options.atoutput, "w") as fl:
                                fl.write(attachments)
                            os.chmod(options.atoutput, chmod)
                        os.umask(oldmask)
                    else:
                        with open(options.atoutput, "w") as fl:
                            fl.write(attachments)
                else:
                    print(attachments)
        except Exception as e:
            sys.stderr.write("nxsfileinfo: '%s'\n"
                             % str(e))
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)


class OrigDatablock(Runner):

    """ OrigDatablock runner"""

    #: (:obj:`str`) command description
    description = "generate description of all scan files"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsfileinfo origdatablock /user/data/scan_12345\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        self._parser.add_argument(
            "-p", "--pid", dest="pid",
            help=("dataset pid"))
        self._parser.add_argument(
            "-i", "--beamtimeid", dest="beamtimeid",
            help=("beamtime id"))
        self._parser.add_argument(
            "-b", "--beamline", dest="beamline",
            help=("beamline"))
        self._parser.add_argument(
            "-w", "--owner-group",
            default="", dest="ownergroup",
            help="owner group name. Default is {beamtimeid}-dmgt")
        self._parser.add_argument(
            "-c", "--access-groups",
            default=None, dest="accessgroups",
            help="access group names separated by commas. "
            "Default is {beamtimeId}-dmgt,{beamtimeid}-clbt,{beamtimeId}-part,"
            "{beamline}dmgt,{beamline}staff")
        self._parser.add_argument(
            "-s", "--skip",
            help="filters for files to be skipped (separated by commas "
            "without spaces). Default: ''. E.g. '*.pyc,*~'",
            dest="skip", default="")
        self._parser.add_argument(
            "-a", "--add",
            help="list of files to be added (separated by commas "
            "without spaces). Default: ''. E.g. 'scan1.nxs,scan2.nxs'",
            dest="add", default="")
        self._parser.add_argument(
            "-x", "--chmod", dest="chmod",
            help=("json metadata file mod bits, e.g. 0o662"))

    def postauto(self):
        """ parser creator after autocomplete run """
        self._parser.add_argument(
            'args', metavar='scan_name', type=str, nargs='+',
            help='scan name')
        self._parser.add_argument(
            "-o", "--output", dest="output",
            help=("output scicat metadata file"))
        self._parser.add_argument(
            "-r", "--relative-path", dest="relpath",
            help=("relative path to scan files"))

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        self.show(options)

    def isotime(self, tme):
        """ returns iso time string

        :returns: iso time
        :rtype: :obj:`str`
        """
        tzone = time.tzname[0]
        if tzone in ['CET', 'CEST']:
            tzone = 'Europe/Berlin'
        fmt = '%Y-%m-%dT%H:%M:%S.%f%z'
        try:
            if sys.version_info >= (3, 9):
                import zoneinfo
                tz = zoneinfo.ZoneInfo(tzone)
                starttime = \
                    datetime.datetime.fromtimestamp(tme).replace(tzinfo=tz)
            else:
                import pytz
                tz = pytz.timezone(tzone)
                starttime = tz.localize(datetime.datetime.fromtimestamp(tme))
        except Exception:
            import tzlocal
            tz = tzlocal.get_localzone()
            starttime = \
                datetime.datetime.fromtimestamp(tme).replace(tzinfo=tz)
        return str(starttime.strftime(fmt))

    def filterout(self, fpath, filters):
        found = False
        if filters:
            for df in filters:
                found = fnmatch.filter([fpath], df)
                if found:
                    break
        return found

    def datafiles(self, scanpath, scdir, scfiles, relpath, filters=None):
        dtfiles = []
        totsize = 0
        pdc = {'7': 'rwx', '6': 'rw-', '5': 'r-x', '4': 'r--',
               '3': '-wx', '2': '-w-', '1': '--x', '0': '---'}
        if scdir and scanpath:
            scdir = os.path.relpath(scdir, scanpath)
        for fl in scfiles:
            rec = {}

            fpath = os.path.join(scanpath, scdir, fl)
            if self.filterout(fpath, filters):
                continue
            status = os.stat(fpath)
            prm = str(oct(status.st_mode)[-3:])
            isdir = 'd' if stat.S_ISDIR(status.st_mode) else '-'
            islink = 'l' if stat.S_ISLNK(status.st_mode) else isdir
            perm = islink + ''.join(pdc.get(x, x) for x in prm)

            path = os.path.join(scdir, fl)
            if path.startswith("./"):
                path = path[2:]
            if relpath:
                path = os.path.join(relpath, path)
            rec["path"] = os.path.normpath(path)
            rec["size"] = status.st_size
            rec["time"] = self.isotime(status.st_ctime)
            try:
                rec["uid"] = pwd.getpwuid(status.st_uid).pw_name
            except Exception:
                rec["uid"] = status.st_uid
            try:
                rec["gid"] = grp.getgrgid(status.st_gid).gr_name
            except Exception:
                rec["gid"] = status.st_gid
            rec["perm"] = perm
            dtfiles.append(rec)
            totsize += rec["size"]
        return dtfiles, totsize

    def datablock(self, options):
        """ dump scan datablock JSON

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        skip = None
        add = []
        if options.skip:
            skip = options.skip.split(',')
        if options.add:
            add = options.add.split(',')

        result = {
        }
        dtfiles = []
        scanfiles = []
        scandirs = []
        totsize = 0
        fscandir = None

        for arg in options.args:
            scandir, scanname = os.path.split(os.path.abspath(arg))
            if not fscandir:
                fscandir = fscandir or scandir
                relpath = options.relpath
            else:
                relpath = os.path.relpath(scandir, fscandir)
                if options.relpath:
                    relpath = os.path.join(options.relpath, relpath)
            for (dirpath, dirnames, filenames) in os.walk(scandir):
                scanfiles = [f for f in filenames if f.startswith(scanname)]
                scandirs = [f for f in dirnames if f.startswith(scanname)]
                break
            flist, tsize = self.datafiles(scandir, "", scanfiles,
                                          relpath, skip)
            dtfiles.extend(flist)
            totsize += tsize

            for fl in add:
                if os.path.isfile(fl):
                    ascandir, ascanname = os.path.split(os.path.abspath(fl))
                    flist, tsize = self.datafiles(
                        scandir, ascandir, [ascanname], relpath)
                    dtfiles.extend(flist)
                    totsize += tsize

            for scdir in scandirs:
                for (dirpath, dirnames, filenames) in os.walk(
                        os.path.join(scandir, scdir)):
                    flist, tsize = self.datafiles(
                        scandir, dirpath, filenames, relpath, skip)
                    dtfiles.extend(flist)
                    totsize += tsize
        result["dataFileList"] = dtfiles
        result["size"] = totsize
        if options.ownergroup:
            result["ownerGroup"] = options.ownergroup
        if options.accessgroups is not None:
            accessgroups = options.accessgroups.split(",")
            result["accessGroups"] = accessgroups
        if options.pid:
            result["datasetId"] = options.pid
        beamtimeid = ""
        if hasattr(options, "beamtimeid") and options.beamtimeid:
            beamtimeid = options.beamtimeid
        if not beamtimeid and "datasetId" in result \
           and result["datasetId"] and \
           len(result["datasetId"].split("/")) > 1:
            bts = result["datasetId"].split("/")
            try:
                int(bts[1])
                beamtimeid = bts[1]
            except Exception:
                try:
                    int(bts[0])
                    beamtimeid = bts[0]
                except Exception:
                    beamtimeid = bts[1]
        if "ownerGroup" not in result and beamtimeid:
            result["ownerGroup"] = "%s-dmgt" % (beamtimeid)
        if "accessGroups" not in result:
            accessgroups = []
            if beamtimeid:
                accessgroups = [
                    "%s-clbt" % (beamtimeid),
                    "%s-part" % (beamtimeid),
                    "%s-dmgt" % (beamtimeid)]
            if hasattr(options, "beamline") and options.beamline:
                accessgroups.extend([
                    "%sdmgt" % (options.beamline),
                    "%sstaff" % (options.beamline)
                ])
            if accessgroups:
                result["accessGroups"] = accessgroups
        return json.dumps(
                result, sort_keys=True, indent=4,
                cls=numpyEncoder)

    def show(self, options):
        """ the main function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        try:
            metadata = self.datablock(options)
            if metadata:
                if options.output:
                    fdir, fn = os.path.split(os.path.abspath(options.output))
                    if not os.path.isdir(fdir):
                        os.makedirs(fdir, exist_ok=True)
                    chmod = None
                    try:
                        chmod = int(options.chmod, 8)
                    except Exception:
                        options.chmod = None

                    if options.chmod:
                        oldmask = os.umask(0)

                        def opener(path, flags):
                            return os.open(path, flags, chmod)
                        try:
                            with open(options.output,
                                      "w", opener=opener) as fl:
                                fl.write(metadata)
                        except Exception:
                            with open(options.output, "w") as fl:
                                fl.write(metadata)
                            os.chmod(options.output, chmod)
                        os.umask(oldmask)
                    else:
                        with open(options.output, "w") as fl:
                            fl.write(metadata)
                else:
                    print(metadata)
        except Exception as e:
            sys.stderr.write("nxsfileinfo: '%s'\n"
                             % str(e))
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)


class Sample(Runner):

    """ Sample runner"""

    #: (:obj:`str`) command description
    description = "generate description of sample"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsfileinfo sample -i petra3/h2o/234234 -d 'HH water' " \
        + "-s ~/cm.json \n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        self._parser.add_argument(
            "-s", "--sample-id", dest="sampleid",
            help=("sample id"))
        self._parser.add_argument(
            "-i", "--beamtimeid", dest="beamtimeid",
            help=("beamtime id"))
        self._parser.add_argument(
            "-b", "--beamline", dest="beamline",
            help=("beamline"))
        self._parser.add_argument(
            "-d", "--description", dest="description",
            help=("sample description"))
        self._parser.add_argument(
            "-r", "--owner", dest="owner",
            help=("sample owner"))
        self._parser.add_argument(
            "-p", "--published", dest="published", action="store_true",
            help=("sample is published"), default=False)
        self._parser.add_argument(
            "-w", "--owner-group",
            default="", dest="ownergroup",
            help="owner group name. Default is {beamtimeid}-dmgt")
        self._parser.add_argument(
            "-c", "--access-groups",
            default=None, dest="accessgroups",
            help="access group names separated by commas. "
            "Default is {beamtimeId}-dmgt,{beamtimeid}-clbt,{beamtimeId}-part,"
            "{beamline}dmgt,{beamline}staff")
        self._parser.add_argument(
            "-x", "--chmod", dest="chmod",
            help=("json metadata file mod bits, e.g. 0o662"))

    def postauto(self):
        """ parser creator after autocomplete run """
        self._parser.add_argument(
            "-m", "--sample-characteristics", dest="characteristicsmeta",
            help=("sample characteristics metadata file"))
        self._parser.add_argument(
            "-o", "--output", dest="output",
            help=("output scicat metadata file"))

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        self.show(options)

    def sample(self, options):
        """ create sample metadata

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        dct = {}
        result = {}

        if hasattr(options, "sampleid") and options.sampleid:
            result["sampleId"] = options.sampleid
        if hasattr(options, "description") and options.description:
            result["description"] = options.description
        if hasattr(options, "owner") and options.owner:
            result["owner"] = options.owner
        if hasattr(options, "published") and options.published:
            result["isPublished"] = True
        else:
            result["isPublished"] = False
        if options.ownergroup:
            result["ownerGroup"] = options.ownergroup
        if hasattr(options, "beamtimeid") and options.beamtimeid:
            if "ownerGroup" not in result:
                result["ownerGroup"] = "%s-dmgt" % (options.beamtimeid)
        if options.accessgroups is not None:
            accessgroups = options.accessgroups.split(",")
            result["accessGroups"] = accessgroups
        if "accessGroups" not in result:
            accessgroups = []
            if hasattr(options, "beamtimeid") and options.beamtimeid:
                accessgroups = [
                    "%s-clbt" % (options.beamtimeid),
                    "%s-part" % (options.beamtimeid),
                    "%s-dmgt" % (options.beamtimeid)]
            if hasattr(options, "beamline") and options.beamline:
                accessgroups.extend([
                    "%sdmgt" % (options.beamline),
                    "%sstaff" % (options.beamline)
                ])
            if accessgroups:
                result["accessGroups"] = accessgroups
        if options.characteristicsmeta:
            with open(options.characteristicsmeta, "r") as fl:
                jstr = fl.read()
                try:
                    dct = json.loads(jstr)
                except Exception:
                    if jstr:
                        nan = float('nan')    # noqa: F841
                        dct = eval(jstr)
        if 'sampleCharacteristics' in dct.keys():
            dct = dct['sampleCharacteristics']
        result['sampleCharacteristics'] = dct
        return json.dumps(
                result, sort_keys=True, indent=4,
                cls=numpyEncoder)

    def show(self, options):
        """ the main function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        try:
            metadata = self.sample(options)
            if metadata:
                if options.output:
                    fdir, fn = os.path.split(os.path.abspath(options.output))
                    if not os.path.isdir(fdir):
                        os.makedirs(fdir, exist_ok=True)
                    chmod = None
                    try:
                        chmod = int(options.chmod, 8)
                    except Exception:
                        options.chmod = None

                    if options.chmod:
                        oldmask = os.umask(0)

                        def opener(path, flags):
                            return os.open(path, flags, chmod)
                        try:
                            with open(options.output,
                                      "w", opener=opener) as fl:
                                fl.write(metadata)
                        except Exception:
                            with open(options.output, "w") as fl:
                                fl.write(metadata)
                            os.chmod(options.output, chmod)
                        os.umask(oldmask)
                    else:
                        with open(options.output, "w") as fl:
                            fl.write(metadata)
                else:
                    print(metadata)
        except Exception as e:
            sys.stderr.write("nxsfileinfo: '%s'\n"
                             % str(e))
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)


class Attachment(Runner):

    """ Attachment runner"""

    #: (:obj:`str`) command description
    description = "generate description of attachment"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsfileinfo attachment -b p00 -i 2342342 -t 'HH water' " \
        + "-o ~/at1.json thumbnail.png \n" \
        + "       nxsfileinfo attachment -b p00 -i 2342342 -t 'HH water' " \
        + "-o ~/at2.json -s pilatus myscan_00123.nxs \n" \
        + "       nxsfileinfo attachment -b p00 -i 2342342 -t 'HH water' " \
        + "-o ~/at2.json  myscan_00124.fio \n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        self._parser.add_argument(
            "-a", "--id", dest="atid",
            help=("attachment id"))
        self._parser.add_argument(
            "-t", "--caption", dest="caption",
            help=("caption text"))
        self._parser.add_argument(
            "-i", "--beamtimeid", dest="beamtimeid",
            help=("beamtime id"))
        self._parser.add_argument(
            "-b", "--beamline", dest="beamline",
            help=("beamline"))
        self._parser.add_argument(
            "-r", "--owner", dest="owner",
            help=("attachment owner"))
        self._parser.add_argument(
            "-w", "--owner-group",
            default="", dest="ownergroup",
            help="owner group name. Default is {beamtimeid}-dmgt")
        self._parser.add_argument(
            "-c", "--access-groups",
            default=None, dest="accessgroups",
            help="access group names separated by commas. "
            "Default is {beamtimeId}-dmgt,{beamtimeid}-clbt,{beamtimeId}-part,"
            "{beamline}dmgt,{beamline}staff")
        self._parser.add_argument(
            "-f", "--file-format", dest="fileformat",
            help=("input file format, e.g. 'nxs'. "
                  "Default is defined by the file extension"))
        self._parser.add_argument(
            "--h5py", action="store_true",
            default=False, dest="h5py",
            help="use h5py module as a nexus reader")
        self._parser.add_argument(
            "--h5cpp", action="store_true",
            default=False, dest="h5cpp",
            help="use h5cpp module as a nexus reader")
        self._parser.add_argument(
            "-x", "--chmod", dest="chmod",
            help=("json metadata file mod bits, e.g. 0o662"))
        self._parser.add_argument(
            "-s", "--signals", dest="signals",
            help=("signals data name(s) separated by comma"))
        self._parser.add_argument(
            "-e", "--axes", dest="axes",
            help=("axis/axes data name(s) separated by comma"))
        self._parser.add_argument(
            "-q", "--scan-command-axes", dest="scancmdaxes",
            default='{"hklscan":"h;k;l","qscan":"qz;qpar"}',
            help=("a JSON dictionary with scan-command axes to override, "
                  "axis/axes data name(s) separated by comma for detectors"
                  " and by semicolon for more plots. Default: "
                  '{"hklscan":"h;k;l","qscan":"qz;qpar"}'))
        self._parser.add_argument(
            "-m", "--frame", dest="frame",
            help=("a frame number for if more 2D images in the data"))
        self._parser.add_argument(
            "--signal-label", dest="slabel", help=("signal label"))
        self._parser.add_argument(
            "--xlabel", dest="xlabel", help=("x-axis label"))
        self._parser.add_argument(
            "--ylabel", dest="ylabel", help=("y-axis label"))
        self._parser.add_argument(
            "-u", "--override", action="store_true",
            default=False, dest="override",
            help="override NeXus entries by script parameters")
        self._parser.add_argument(
            "--parameters-in-caption", action="store_true",
            default=False, dest="ppflag",
            help="add plot paramters to the caption")
        self._parser.add_argument(
            "-n", "--nexus-path",
            help="base nexus path to element to be shown"
            " If the path is '' the default group is shown. "
            "The default: ''",
            dest="nexuspath", default="")

    def postauto(self):
        """ parser creator after autocomplete run """
        self._parser.add_argument(
            "-o", "--output", dest="output",
            help=("output scicat metadata file"))
        self._parser.add_argument(
            'args', metavar='image_file', type=str, nargs="*",
            help='png or NeXus image file name')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        if options.h5cpp:
            writer = "h5cpp"
        elif options.h5py:
            writer = "h5py"
        elif "h5cpp" in WRITERS.keys():
            writer = "h5cpp"
        else:
            writer = "h5py"
        if (options.h5cpp and options.h5py) or writer not in WRITERS.keys():
            sys.stderr.write("nxsfileinfo: Writer '%s' cannot be opened\n"
                             % writer)
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)

        root = None
        nxfl = None
        if not hasattr(options, "fileformat"):
            options.fileformat = ""
        if options.args:
            wrmodule = WRITERS[writer.lower()]
            if not options.fileformat:
                rt, ext = os.path.splitext(options.args[0])
                if ext and len(ext) > 1 and ext.startswith("."):
                    options.fileformat = ext[1:]
            try:
                if options.fileformat in ['nxs', 'h5', 'nx', 'ndf']:
                    nxfl = filewriter.open_file(
                        options.args[0], readonly=True,
                        writer=wrmodule)
                    root = nxfl.root()
                elif options.fileformat in ['fio']:
                    with open(options.args[0]) as fl:
                        root = fl.read()
                elif options.fileformat in ['png']:
                    with open(options.args[0], "rb") as fl:
                        root = "data:image/png;base64," + \
                            base64.b64encode(fl.read()).decode('utf-8')
            except Exception:
                sys.stderr.write("nxsfileinfo: File '%s' cannot be opened\n"
                                 % options.args[0])
                sys.stderr.flush()
                self._parser.print_help()
                sys.exit(255)

        self.show(root, options)
        if nxfl is not None:
            nxfl.close()

    def attachment(self, root, options):
        """ get metadata from nexus and beamtime file

        :param root: nexus file root
        :type root: :class:`filewriter.FTGroup`
        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: atttachment metadata
        :rtype: :obj:`str`
        """
        result = {}

        if hasattr(options, "atid") and options.atid:
            result["id"] = options.atid
        if hasattr(options, "caption") and options.caption:
            result["caption"] = options.caption
        if options.ownergroup:
            result["ownerGroup"] = options.ownergroup
        if hasattr(options, "beamtimeid") and options.beamtimeid:
            if "ownerGroup" not in result:
                result["ownerGroup"] = "%s-dmgt" % (options.beamtimeid)
        if options.accessgroups is not None:
            accessgroups = options.accessgroups.split(",")
            result["accessGroups"] = accessgroups
        if "accessGroups" not in result:
            accessgroups = []
            if hasattr(options, "beamtimeid") and options.beamtimeid:
                accessgroups = [
                    "%s-clbt" % (options.beamtimeid),
                    "%s-part" % (options.beamtimeid),
                    "%s-dmgt" % (options.beamtimeid)]
            if hasattr(options, "beamline") and options.beamline:
                accessgroups.extend([
                    "%sdmgt" % (options.beamline),
                    "%sstaff" % (options.beamline)
                ])
            if accessgroups:
                result["accessGroups"] = accessgroups

        if not hasattr(options, "fileformat"):
            options.fileformat = ""
        if options.args and not options.fileformat:
            rt, ext = os.path.splitext(options.args[0])
            if ext and len(ext) > 1 and ext.startswith("."):
                options.fileformat = ext[1:]

        if root is not None:
            if options.fileformat in ['png']:
                result["thumbnail"] = root
            elif MATPLOTLIB:
                signals = None
                axes = []
                xlabel = None
                ylabel = None
                slabel = None
                frame = None
                if options.signals:
                    signals = options.signals.split(",")
                if options.axes:
                    axes = options.axes.split(",")
                if options.frame is not None:
                    try:
                        frame = int(options.frame)
                    except Exception:
                        frame = None
                if options.xlabel:
                    xlabel = options.xlabel
                if options.ylabel:
                    ylabel = options.ylabel
                if options.slabel:
                    slabel = options.slabel
                if options.fileformat in ['nxs', 'h5', 'nx', 'ndf']:
                    tn, pars = self._nxsplot(
                        root, signals, axes, slabel, xlabel, ylabel, frame,
                        options.caption, options.override, options.scancmdaxes,
                        options.nexuspath)
                    if tn:
                        result["thumbnail"] = tn
                        if "caption" not in result:
                            result["caption"] = ""
                        if options.ppflag:
                            result["caption"] += " " + pars

                elif options.fileformat in ['fio']:
                    nxsparser = FIOFileParser(root)
                    nxsparser.oned = True
                    nxsparser.maxonedsize = -1
                    nxsparser.parseMeta()
                    data = None
                    sdata = None
                    adata = None
                    signal = None
                    params = {}
                    scancmd = None
                    if nxsparser.description and nxsparser.columns:
                        desc = nxsparser.description[0]
                        sm = None
                        if "scientificMetadata" in desc.keys():
                            sm = desc["scientificMetadata"]
                        if sm and "data" in sm.keys():
                            data = sm["data"]
                        if sm and "parameters" in sm.keys():
                            params = sm["parameters"]
                        if sm:
                            if "ScanCommand" in sm and sm["ScanCommand"]:
                                scancmd = sm["ScanCommand"]
                                ax = self._axesfromcommand(
                                    scancmd, options.scancmdaxes, data, axes)
                                if ax:
                                    axes = ax
                        if not signal and 'signalcounter' in params \
                                and params['signalcounter']:
                            if data and params['signalcounter'] in data:
                                signal = params['signalcounter']
                                sdata = data[signal]
                                if not slabel:
                                    slabel = signal
                        if not signal and 'signal' in params \
                                and params['signal']:
                            if data and params['signal'] in data:
                                signal = params['signal']
                                sdata = data[signal]
                                if not slabel:
                                    slabel = signal
                        if not signal or options.override:
                            if data and signals:
                                for sg in signals:
                                    if sg and sg in data.keys():
                                        signal = sg
                                        sdata = data[signal]
                                        if not slabel:
                                            slabel = signal
                                        break
                        if not signal:
                            if len(nxsparser.columns) > 1 and \
                                    len(nxsparser.columns[1]) > 1:
                                sdata = nxsparser.columns[1][1]
                                if not slabel:
                                    slabel = nxsparser.columns[1][0]
                            elif len(nxsparser.columns) > 0 and \
                                    len(nxsparser.columns[0]) > 1:
                                sdata = nxsparser.columns[0][1]
                                if not slabel:
                                    slabel = nxsparser.columns[0][0]
                        axis = None
                        if data and axes:
                            for ax in axes:
                                if ax and ax in data.keys():
                                    axis = ax
                                    adata = data[ax]
                                    if not xlabel:
                                        xlabel = ax
                                    break

                        if not axis and len(nxsparser.columns) > 1 and \
                                len(nxsparser.columns[0]) > 1:
                            adata = nxsparser.columns[0][1]
                            if not xlabel:
                                xlabel = nxsparser.columns[0][0]
                        if sdata:
                            result["thumbnail"], pars = self._plot1d(
                                sdata, adata, xlabel, slabel, options.caption,
                                scancmd=scancmd)
                        if "caption" not in result:
                            result["caption"] = ""
                        if options.ppflag:
                            result["caption"] += " " + pars

        if "thumbnail" in result and result["thumbnail"]:
            if "caption" not in result:
                result["caption"] = ""
            return json.dumps(
                result, sort_keys=True, indent=4,
                cls=numpyEncoder)

    def _axesfromcommand(self, scmd, scmdaxes, data, useraxes=None):
        """ create plot from nexus file

        :param scmd: scan command
        :type scmd: :obj:`str`
        :param scmdaxes: JSON dictionry with scan command axes
        :type scmdaxes: :obj:`str`
        :param data: nxdata nexus file
        :type data: class:`filewriter.FTGroup` or dict <:obj:`str`, `any`>
        :returns: axis from scan command
        :rtype: :obj:`str`
        """

        axes = []
        useraxes = useraxes or []
        try:
            if scmdaxes:
                scaxes = json.loads(scmdaxes)
                if scaxes and isinstance(scaxes, dict):
                    scmd1 = [sc for sc in scmd.split(" ") if sc][0]
                    if scmd1 in scaxes:
                        axs = scaxes[scmd1].split(",")
                        for ax in axs:
                            maxsz = 0
                            ta = ""
                            for aa in ax.split(";"):
                                adata = None
                                if isinstance(data, dict):
                                    if aa and aa in data.keys():
                                        adata = data[aa]
                                elif hasattr(data, "names") and \
                                        hasattr(data, "open"):
                                    if aa and aa in data.names():
                                        try:
                                            adata = data.open(aa).read()
                                        except Exception:
                                            pass
                                if adata is not None:
                                    mx = max(adata) - min(adata)
                                    if mx > maxsz:
                                        maxsz = mx
                                        ta = aa
                            if maxsz:
                                axes = [ta]
                                break
        except Exception:
            pass
        if not axes and not useraxes:
            scmds = [sc for sc in scmd.split(" ") if sc]
            if len(scmds) > 1:
                aa = scmds[1]
                if isinstance(data, dict):
                    if aa and aa in data.keys():
                        axes = [aa]
                elif hasattr(data, "names") and \
                        aa and aa in data.names():
                    axes = [aa]
        return axes

    def _nxsplot(self, root, signals, axes, slabel, xlabel, ylabel, frame,
                 title, override=False, scmdaxes=None, nexuspath=None):
        """ create plot from nexus file


        :param root: nexus file root
        :type root: class:`filewriter.FTGroup`
        :param signals: signal names
        :type signals: :obj:`list`<:obj:`str`>
        :param axes: axes names
        :type axes: :obj:`list`<:obj:`str`>
        :param slabel: s-label
        :type slabel: :obj:`str`
        :param xlabel: x-label
        :type xlabel: :obj:`str`
        :param ylabel: y-label
        :type ylabel: :obj:`str`
        :param title: title
        :type title: :obj:`str`
        :param scmdaxes: JSON dictionry with scan command axes
        :type scmdaxes: :obj:`str`
        :param nexuspath: attachment nexuspath
        :type nexuspath: :obj:`str`
        :returns: thumbnail string
        :rtype: :obj:`str`
        """
        # print(signals)
        sgnode = root.default_field(signals, nexuspath)
        nxdata = None
        entry = None
        signal = None
        # print(sgnode)
        if sgnode is not None:
            nxdata = sgnode.parent
            if nxdata is not None:
                if override and signals:
                    for sg in signals:
                        if sg in nxdata.names():
                            sgnode = nxdata.open(sg)
                            signal = sg
                elif not signal:
                    signal = sgnode.name
            entry = nxdata.parent
        if nxdata is None:
            entry = None
            attrs = root.attributes
            if hasattr(root, "names") and "default" in attrs.names():
                nname = filewriter.first(attrs["default"].read())
                if nname in root.names():
                    entry = root.open(nname)
            if entry is None:
                enames = ["entry", "scan"]
                for enm in enames:
                    if enm in root.names():
                        entry = root.open(enm)
                        break
            if entry is not None:
                attrs = entry.attributes
                if hasattr(entry, "names") and "default" in attrs.names():
                    nname = filewriter.first(attrs["default"].read())
                    if nname in entry.names():
                        nxdata = entry.open(nname)
            if entry is not None and nxdata is None:
                enames = ["data"]
                for enm in enames:
                    if enm in entry.names():
                        entry = entry.open(enm)
                        break
            if nxdata is not None:
                attrs = nxdata.attributes
                if hasattr(nxdata, "names") and "signal" in attrs.names():
                    nname = filewriter.first(attrs["signal"].read())
                    if nname in nxdata.names():
                        sgnode = nxdata.open(nname)
            if nxdata is not None and (override or sgnode is None) and \
               signal in nxdata.names():
                sgnode = nxdata.open(signal)
            if sgnode is None and nxdata is not None and \
                    "data" in nxdata.names():
                sgnode = nxdata.open("data")
                signal = "data"

        if sgnode is not None:
            try:
                dtshape = sgnode.shape
                dtsize = sgnode.size
                # print(dtshape)
                # print(nxdata.names())
                # print(signal)
                # print(slabel)
                # print(xlabel)
                # print(ylabel)
                scommand = None
                if len(dtshape) == 1 and dtsize > 1:
                    if hasattr(entry, "names") and \
                            hasattr(nxdata, "names") and \
                            "program_name" in entry.names():
                        pn = entry.open("program_name")
                        attr = pn.attributes
                        names = [att.name for att in attr]
                        if "scan_command" in names:
                            scommand = filewriter.first(
                                attr["scan_command"].read())
                            ax = self._axesfromcommand(
                                scommand, scmdaxes, nxdata, axes)
                            if ax:
                                axes = ax
                    return self._nxsplot1d(
                        sgnode, signal, axes, slabel, xlabel, ylabel,
                        title, override, scancmd=scommand)
                elif len(dtshape) == 2 and dtsize > 1:
                    return self._nxsplot2d(
                        sgnode, signal, slabel, title, override,
                        scancmd=scommand)

                elif len(dtshape) == 3 and dtsize > 1:
                    return self._nxsplot3d(
                        sgnode, signal, slabel, title, override, frame,
                        scancmd=scommand)
            except Exception:
                return None, None
        return None, None

    def _nxsplot3d(self, sgnode, signal, slabel, title,
                   override=False, frame=None, scancmd=None):
        """ create plot 1d from nexus file


        :param sgnode: nexus signal field node
        :type sgnode: class:`filewriter.FTField`
        :param signal: signal name
        :type signal: :obj:`str`
        :param slabel: s-label
        :type slabel: :obj:`str`
        :param title: title
        :type title: :obj:`str`
        :param override: override nexus attributes flag
        :type override: :obj:`bool`
        :param frame: frame number to plot
        :type frame: :obj:`int`
        :param scancmd: scan command
        :type scancmd: :obj:`str`
        :returns: thumbnail string
        :rtype: :obj:`str`
        """
        signal = sgnode.name
        nxdata = sgnode.parent

        shape = sgnode.shape
        mxframe = shape[0]
        if frame is None:
            frame = int(mxframe / 2)
        if frame and frame < 0:
            frame = mxframe + frame
        if frame and frame < 0:
            frame = 0
        if frame and frame >= mxframe:
            frame = mxframe - 1

        sdata = sgnode[frame, :, :]
        sunits = None
        slname = None
        if "units" in sgnode.attributes.names():
            sunits = filewriter.first(
                sgnode.attributes["units"].read())
        if "long_name" in sgnode.attributes.names():
            slname = filewriter.first(
                sgnode.attributes["long_name"].read())
        if not override or not slabel:
            if slname:
                slabel = "%s[%s]" % (slname, frame)
            else:
                slabel = "%s[%s]" % (signal, frame)
            if sunits:
                slabel = "%s (%s)" % (slabel, sunits)
        if (not override or not title) and nxdata.parent is not None and \
                "title" in nxdata.parent.names():
            title = filewriter.first(nxdata.parent.open("title").read())
        return self._plot2d(sdata, slabel, title, scancmd=scancmd)

    def _nxsplot2d(self, sgnode, signal, slabel, title,
                   override=False, frame=None, scancmd=None):
        """ create plot 1d from nexus file


        :param sgnode: nexus signal field node
        :type sgnode: class:`filewriter.FTField`
        :param signal: signal name
        :type signal: :obj:`str`
        :param slabel: s-label
        :type slabel: :obj:`str`
        :param title: title
        :type title: :obj:`str`
        :param override: override nexus attributes flag
        :type override: :obj:`bool`
        :param frame: frame number to display
        :type frame: :obj:`int`
        :param scancmd: scan command
        :type scancmd: :obj:`str`
        :returns: thumbnail string
        :rtype: :obj:`str`
        """
        signal = sgnode.name
        nxdata = sgnode.parent

        sdata = sgnode.read()
        sunits = None
        slname = None
        if "units" in sgnode.attributes.names():
            sunits = filewriter.first(
                sgnode.attributes["units"].read())
        if "long_name" in sgnode.attributes.names():
            slname = filewriter.first(
                sgnode.attributes["long_name"].read())
        if not override or not slabel:
            if slname:
                slabel = slname
            elif not slabel:
                slabel = signal
            if sunits:
                slabel = "%s (%s)" % (slabel, sunits)
        if (not override or not title) and nxdata.parent is not None and \
                "title" in nxdata.parent.names():
            title = filewriter.first(nxdata.parent.open("title").read())
        return self._plot2d(sdata, slabel, title, scancmd=scancmd)

    def _nxsplot1d(self, sgnode, signal, axes, slabel, xlabel, ylabel,
                   title, override=False, scancmd=None):
        """ create plot 1d from nexus file


        :param sgnode: nexus signal field node
        :type sgnode: class:`filewriter.FTField`
        :param signal: signal name
        :type signal: :obj:`str`
        :param axes: axes names
        :type axes: :obj:`list`<:obj:`str`>
        :param slabel: s-label
        :type slabel: :obj:`str`
        :param xlabel: x-label
        :type xlabel: :obj:`str`
        :param ylabel: y-label
        :type ylabel: :obj:`str`
        :param title: title
        :type title: :obj:`str`
        :param override: override nexus attributes flag
        :type override: :obj:`bool`
        :param scancmd: scan command
        :type scancmd: :obj:`str`
        :returns: thumbnail string
        :rtype: :obj:`str`,
        """
        signal = sgnode.name
        nxdata = sgnode.parent

        attrs = nxdata.attributes
        if hasattr(nxdata, "names") and "axes" in attrs.names():

            naxes = filewriter.first(attrs["axes"].read())
            if not override and naxes:
                axes = [naxes]
        adata = []
        anode = None
        axis = ""
        if axes:
            for ax in axes:
                if ax in nxdata.names():
                    try:
                        anode = nxdata.open(ax)
                        axis = ax
                        adata = anode.read()
                        break
                    except Exception:
                        pass
        sdata = sgnode.read()
        sunits = None
        aunits = None
        slname = None
        alname = None
        if "units" in sgnode.attributes.names():
            sunits = filewriter.first(
                sgnode.attributes["units"].read())
        if "long_name" in sgnode.attributes.names():
            slname = filewriter.first(
                sgnode.attributes["long_name"].read())
        if not override or not slabel:
            if slname:
                slabel = slname
            elif not slabel:
                slabel = signal
            if sunits:
                slabel = "%s (%s)" % (slabel, sunits)
        if anode is not None and "units" in anode.attributes.names():
            aunits = filewriter.first(anode.attributes["units"].read())
        if anode is not None and "long_name" in anode.attributes.names():
            alname = filewriter.first(
                anode.attributes["long_name"].read())
        if (not override or not xlabel) and axes and axes[0]:
            if alname:
                xlabel = alname
            elif not xlabel and axis:
                xlabel = axis
            if aunits:
                xlabel = "%s (%s)" % (xlabel, aunits)
        if (not override or not title) and nxdata.parent is not None and \
                "title" in nxdata.parent.names():
            title = filewriter.first(nxdata.parent.open("title").read())
        return self._plot1d(
            sdata, adata, xlabel, slabel, title, scancmd=scancmd)

    def _plot1d(self, data, axis, xlabel, ylabel, title, maxo=25,
                scancmd=None, maxtitle=68):
        """ create oned thumbnail plot


        :param data: 1d signal data
        :type data: :obj:`list`<:obj:`float`> or :obj:`list`<:obj:`int`>
        :param axis: 1d axis data
        :type axis: :obj:`list`<:obj:`float`> or :obj:`list`<:obj:`int`>
        :param xlabel: x-label
        :type xlabel: :obj:`str`
        :param ylabel: y-label
        :type ylabel: :obj:`str`
        :param title: title
        :type title: :obj:`str`
        :param maxo:  maximal number of point to display dots
        :type maxo: :obj:`int`
        :param scancmd: scan command
        :type scancmd: :obj:`str`
        :param maxtitle: maximal title size
        :type maxtitle: :obj:`int`
        :returns: thumbnail string
        :rtype: :obj:`str`
        """

        pars = {}
        matplotlib.interactive(False)
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()

        if scancmd and len(scancmd) > maxtitle:
            # scancmd = splittext(scancmd)
            scancmd = scancmd[:maxtitle]
        if ylabel:
            if title:
                title = title
            else:
                title = ylabel

        if axis is not None and len(axis) == len(data):
            if len(data) < maxo:
                ax.plot(axis, data, 'o', axis, data)
            else:
                ax.plot(axis, data)
            ax.set(xlabel=xlabel, ylabel=ylabel, title=scancmd)
            if xlabel:
                pars["xlabel"] = xlabel
        else:
            axis = list(range(len(data)))
            if len(data) < maxo:
                ax.plot(axis, data, 'o', axis, data)
            else:
                ax.plot(axis, data)
            ax.set(ylabel=ylabel, title=scancmd)
        fig.suptitle(title, fontsize=20, y=1)
        if ylabel:
            pars["ylabel"] = ylabel
        if title:
            pars["suptitle"] = title
        if scancmd:
            pars["title"] = scancmd

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close(fig)
        buffer.seek(0)
        png_image = buffer.getvalue()
        buffer.close()
        # with open("/tmp/myttt.png", "wb") as fl:
        #     fl.write(png_image)
        thumbnail = base64.b64encode(png_image)
        thumbnail = "data:image/png;base64," + thumbnail.decode('utf-8')
        return thumbnail, json.dumps(pars)

    def _plot2d(self, data, slabel, title, maxratio=10, scancmd=None,
                maxtitle=68):
        """ create oned thumbnail plot


        :param data: 1d signal data
        :type data: :obj:`list`<:obj:`float`> or :obj:`list`<:obj:`int`>
        :param slabel: signal-label
        :type slabel: :obj:`str`
        :param title: title
        :type title: :obj:`str`
        :param maxratio:  max ratio to do not change aspect ratio
        :type maxratio: :obj:`float`
        :param scancmd: scan command
        :type scancmd: :obj:`str`
        :param maxtitle: maximal title size
        :type maxtitle: :obj:`int`
        :returns: thumbnail string
        :rtype: :obj:`str`
        """
        pars = {}
        matplotlib.interactive(False)
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        shape = data.shape
        if int(shape[0]/shape[1]) > maxratio or \
                int(shape[1]/shape[0]) > maxratio:
            ax.imshow(data, aspect='auto')
            pars["aspect"] = 'auto'
        else:
            ax.imshow(data)
        if scancmd and len(scancmd) > maxtitle:
            scancmd = scancmd[:maxtitle]
            # scancmd = splittext(scancmd)
        if slabel:
            if title:
                title = "%s: %s" % (title, slabel)
            else:
                title = slabel

        if title:
            fig.suptitle(title, fontsize=20, y=1)
            pars["suptitle"] = title
        if scancmd:
            ax.set(title=scancmd)
            pars["title"] = scancmd

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close(fig)
        buffer.seek(0)
        png_image = buffer.getvalue()
        buffer.close()
        thumbnail = base64.b64encode(png_image)
        thumbnail = "data:image/png;base64," + thumbnail.decode('utf-8')
        return thumbnail, json.dumps(pars)

    def show(self, root, options):
        """ the main function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :param root: nexus file root
        :type root: :class:`filewriter.FTGroup`
        """
        try:
            metadata = self.attachment(root, options)
            if metadata:
                if options.output:
                    fdir, fn = os.path.split(os.path.abspath(options.output))
                    if not os.path.isdir(fdir):
                        os.makedirs(fdir, exist_ok=True)
                    chmod = None
                    try:
                        chmod = int(options.chmod, 8)
                    except Exception:
                        options.chmod = None

                    if options.chmod:
                        oldmask = os.umask(0)

                        def opener(path, flags):
                            return os.open(path, flags, chmod)
                        try:
                            with open(options.output,
                                      "w", opener=opener) as fl:
                                fl.write(metadata)
                        except Exception:
                            with open(options.output, "w") as fl:
                                fl.write(metadata)
                            os.chmod(options.output, chmod)
                        os.umask(oldmask)
                    else:
                        with open(options.output, "w") as fl:
                            fl.write(metadata)
                else:
                    print(metadata)
        except Exception as e:
            sys.stderr.write("nxsfileinfo: '%s'\n"
                             % str(e))
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)


class Instrument(Runner):

    """ Instrument runner"""

    #: (:obj:`str`) command description
    description = "generate description of instrument"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsfileinfo instrument -p /petra3/p00 -n P00 -m " \
        + "~/cm.json \n" \
        + "\n"

    def create(self):
        """ creates parser

        """
        self._parser.add_argument(
            "-p", "--pid", dest="pid",
            help=("instrument pid"))
        self._parser.add_argument(
            "-n", "--name", dest="name",
            help=("instrument name"))
        self._parser.add_argument(
            "-i", "--beamtimeid", dest="beamtimeid",
            help=("beamtime id"))
        self._parser.add_argument(
            "-b", "--beamline", dest="beamline",
            help=("beamline"))
        self._parser.add_argument(
            "-w", "--owner-group",
            default="", dest="ownergroup",
            help="owner group name. Default is {beamtimeid}-dmgt")
        self._parser.add_argument(
            "-c", "--access-groups",
            default=None, dest="accessgroups",
            help="access group names separated by commas. "
            "Default is {beamtimeId}-dmgt,{beamtimeid}-clbt,{beamtimeId}-part,"
            "{beamline}dmgt,{beamline}staff")
        self._parser.add_argument(
            "-x", "--chmod", dest="chmod",
            help=("json metadata file mod bits, e.g. 0o662"))

    def postauto(self):
        """ parser creator after autocomplete run """
        self._parser.add_argument(
            "-m", "--custom-metadata", dest="custommeta",
            help=("instrument characteristics metadata file"))
        self._parser.add_argument(
            "-o", "--output", dest="output",
            help=("output scicat metadata file"))

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        self.show(options)

    def instrument(self, options):
        """ create instrument metadata

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        dct = {}
        result = {}

        if hasattr(options, "pid") and options.pid:
            result["pid"] = options.pid
        if hasattr(options, "name") and options.name:
            result["name"] = options.name
        if options.ownergroup:
            result["ownerGroup"] = options.ownergroup
        if hasattr(options, "beamtimeid") and options.beamtimeid:
            if "ownerGroup" not in result:
                result["ownerGroup"] = "%s-dmgt" % (options.beamtimeid)
        if options.accessgroups is not None:
            accessgroups = options.accessgroups.split(",")
            result["accessGroups"] = accessgroups
        if "accessGroups" not in result:
            accessgroups = []
            if hasattr(options, "beamtimeid") and options.beamtimeid:
                accessgroups = [
                    "%s-clbt" % (options.beamtimeid),
                    "%s-part" % (options.beamtimeid),
                    "%s-dmgt" % (options.beamtimeid)]
            if hasattr(options, "beamline") and options.beamline:
                accessgroups.extend([
                    "%sdmgt" % (options.beamline),
                    "%sstaff" % (options.beamline)
                ])
            if accessgroups:
                result["accessGroups"] = accessgroups
        if options.custommeta:
            with open(options.custommeta, "r") as fl:
                jstr = fl.read()
                try:
                    dct = json.loads(jstr)
                except Exception:
                    if jstr:
                        nan = float('nan')    # noqa: F841
                        dct = eval(jstr)
        if 'customMetadata' in dct.keys():
            dct = dct['customMetadata']
        result['customMetadata'] = dct
        return json.dumps(
                result, sort_keys=True, indent=4,
                cls=numpyEncoder)

    def show(self, options):
        """ the main function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        """
        try:
            metadata = self.instrument(options)
            if metadata:
                if options.output:
                    fdir, fn = os.path.split(os.path.abspath(options.output))
                    if not os.path.isdir(fdir):
                        os.makedirs(fdir, exist_ok=True)
                    chmod = None
                    try:
                        chmod = int(options.chmod, 8)
                    except Exception:
                        options.chmod = None

                    if options.chmod:
                        oldmask = os.umask(0)

                        def opener(path, flags):
                            return os.open(path, flags, chmod)
                        try:
                            with open(options.output,
                                      "w", opener=opener) as fl:
                                fl.write(metadata)
                        except Exception:
                            with open(options.output, "w") as fl:
                                fl.write(metadata)
                            os.chmod(options.output, chmod)
                        os.umask(oldmask)
                    else:
                        with open(options.output, "w") as fl:
                            fl.write(metadata)
                else:
                    print(metadata)
        except Exception as e:
            sys.stderr.write("nxsfileinfo: '%s'\n"
                             % str(e))
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)


class Field(Runner):

    """ Field runner"""

    #: (:obj:`str`) command description
    description = "show field information for the nexus file"
    #: (:obj:`str`) command epilog
    epilog = "" \
        + " examples:\n" \
        + "       nxsfileinfo field /user/data/myfile.nxs\n" \
        + "       nxsfileinfo field /user/data/myfile.nxs -g\n" \
        + "       nxsfileinfo field /user/data/myfile.nxs -s\n" \
        + "\n"

    def create(self):
        """ creates parser

        """
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
            help="full_path filters (separated by commas "
            "without spaces). Default: '*'. E.g. '*:NXsample/*'",
            dest="filters", default="")
        self._parser.add_argument(
            "-v", "--values",
            help="field names which value should be stored"
            " (separated by commas "
            "without spaces). Default: depends_on",
            dest="values", default="")
        self._parser.add_argument(
            "-g", "--geometry", action="store_true",
            default=False, dest="geometry",
            help="perform geometry full_path filters, i.e."
            "*:NXtransformations/*,*/depends_on. "
            "It works only when  -f is not defined")
        self._parser.add_argument(
            "-s", "--source", action="store_true",
            default=False, dest="source",
            help="show datasource parameters")
        self._parser.add_argument(
            "--h5py", action="store_true",
            default=False, dest="h5py",
            help="use h5py module as a nexus reader")
        self._parser.add_argument(
            "--h5cpp", action="store_true",
            default=False, dest="h5cpp",
            help="use h5cpp module as a nexus reader")

    def postauto(self):
        """ parser creator after autocomplete run """
        self._parser.add_argument(
            'args', metavar='nexus_file', type=str, nargs=1,
            help='new nexus file name')

    def run(self, options):
        """ the main program function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :returns: output information
        :rtype: :obj:`str`
        """
        if options.h5cpp:
            writer = "h5cpp"
        elif options.h5py:
            writer = "h5py"
        elif "h5cpp" in WRITERS.keys():
            writer = "h5cpp"
        else:
            writer = "h5py"
        if (options.h5cpp and options.h5py) or writer not in WRITERS.keys():
            sys.stderr.write("nxsfileinfo: Writer '%s' cannot be opened\n"
                             % writer)
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)
        wrmodule = WRITERS[writer.lower()]
        try:
            fl = filewriter.open_file(
                options.args[0], readonly=True,
                writer=wrmodule)
        except Exception:
            sys.stderr.write("nxsfileinfo: File '%s' cannot be opened\n"
                             % options.args[0])
            sys.stderr.flush()
            self._parser.print_help()
            sys.exit(255)

        root = fl.root()
        self.show(root, options)
        fl.close()

    def show(self, root, options):
        """ the main function

        :param options: parser options
        :type options: :class:`argparse.Namespace`
        :param root: nexus file root
        :type root: class:`filewriter.FTGroup`
        """
        #: (:obj:`list`< :obj:`str`>)   \
        #     parameters which have to exists to be shown
        toshow = None

        #: (:obj:`list`< :obj:`str`>)  full_path filters
        filters = []

        #: (:obj:`list`< :obj:`str`>)  column headers
        headers = ["nexus_path", "source_name", "units",
                   "dtype", "shape", "value"]
        if options.geometry:
            filters = ["*:NXtransformations/*", "*/depends_on"]
            headers = ["nexus_path", "source_name", "units",
                       "trans_type", "trans_vector", "trans_offset",
                       "depends_on"]
        if options.source:
            headers = ["source_name", "nexus_type", "shape", "strategy",
                       "source"]
            toshow = ["source_name"]
        #: (:obj:`list`< :obj:`str`>)  field names which value should be stored
        values = ["depends_on"]

        if options.headers:
            headers = options.headers.split(',')
        if options.filters:
            filters = options.filters.split(',')
        if options.values:
            values = options.values.split(',')

        nxsparser = NXSFileParser(root)
        nxsparser.filters = filters
        nxsparser.valuestostore = values
        nxsparser.parse()

        description = []
        ttools = TableTools(nxsparser.description, toshow)
        ttools.title = "File name: '%s'" % options.args[0]
        ttools.headers = headers
        description.extend(ttools.generateList())
        print("\n".join(description))


def main():
    """ the main program function
    """

    description = "Command-line tool for showing meta data" \
                  + " from Nexus Files"

    epilog = 'For more help:\n  nxsfileinfo <sub-command> -h'
    parser = NXSArgParser(
        description=description, epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.cmdrunners = [('field', Field),
                         ('general', General),
                         ('metadata', Metadata),
                         ('groupmetadata', GroupMetadata),
                         ('origdatablock', OrigDatablock),
                         ('sample', Sample),
                         ('instrument', Instrument),
                         ('attachment', Attachment),
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

    result = runners[options.subparser].run(options)
    if result and str(result).strip():
        print(result)


if __name__ == "__main__":
    main()
