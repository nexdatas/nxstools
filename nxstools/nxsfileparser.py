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

""" NeXus main metadata viewer """

from . import filewriter
import fnmatch
import json
import sys
import xml.etree.ElementTree as et
import numpy as np
import math
import time
import dateutil.parser
import re
from lxml.etree import XMLParser

from nxstools.nxsparser import ParserTools


class numpyEncoder(json.JSONEncoder):
    """ numpy json encoder with list
    """

    def default(self, obj):
        """ default encoder

        :param obj: numpy array object
        :type obj: :obj:`object` or `any`
        """
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except Exception:
                return obj.decode()
        return json.JSONEncoder.default(self, obj)


class numpyEncoderNull(numpyEncoder):
    """ numpy json encoder with list with nan/inf to null
    """
    def encode(self, obj, *args, **kwargs):
        return numpyEncoder.encode(self, infNaN2None(obj), *args, **kwargs)


def infNaN2None(obj):
    """ replace inf and NaN to None
    """
    if isinstance(obj, dict):
        return {ky: infNaN2None(vl) for ky, vl in obj.items()}
    elif isinstance(obj, list):
        return [infNaN2None(it) for it in obj]
    elif isinstance(obj, float) and math.isinf(obj):
        return None
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


_regex = r'^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-' \
    r'(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])' \
    r'(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$'

_match_iso8601 = re.compile(_regex).match


def isoDate(text):
    """ convert date to iso format

    :param text: date text to convert
    :type text: :obj:`str`
    :returns: date in iso format
    :rtype: :obj:`str`
    """
    result = ""
    try:
        try:
            if _match_iso8601(text) is not None:
                result = text
        except Exception:
            pass
        if not result:
            date = dateutil.parser.parse(text)
            fmt = '%Y-%m-%dT%H:%M:%S.%f%z'
            if date.tzinfo is None:
                tzone = time.tzname[0]
                if tzone in ['CET', 'CEST']:
                    tzone = 'Europe/Berlin'
                try:
                    if sys.version_info >= (3, 9):
                        import zoneinfo
                        tz = zoneinfo.ZoneInfo(tzone)
                        date = date.replace(tzinfo=tz)
                    else:
                        import pytz
                        tz = pytz.timezone(tzone)
                        date = tz.localize(date)
                except Exception:
                    import tzlocal
                    tz = tzlocal.get_localzone()
                    date = date.replace(tzinfo=tz)
            result = str(date.strftime(fmt))
    except Exception:
        result = text
    return result


def getdsname(xmlstring):
    """ provides datasource name from datasource xml string

    :param xmlstring: datasource xml string
    :type xmlstring: :obj:`str`
    """

    if sys.version_info > (3,):
        node = et.fromstring(
            bytes(xmlstring, "UTF-8"),
            parser=XMLParser(collect_ids=False))
    else:
        node = et.fromstring(
            xmlstring,
            parser=XMLParser(collect_ids=False))
    if node.tag == 'datasource':
        nodes = [node]
    else:
        nodes = node.findall(".//datasource")
    dsname = ""
    if nodes and "name" in nodes[0].attrib:
        dsname = nodes[0].attrib["name"]
    return dsname or ""


def getdstype(xmlstring):
    """ provides datasource type from datasource xml string

    :param xmlstring: datasource xml string
    :type xmlstring: :obj:`str`
    """

    if sys.version_info > (3,):
        node = et.fromstring(
            bytes(xmlstring, "UTF-8"),
            parser=XMLParser(collect_ids=False))
    else:
        node = et.fromstring(
            xmlstring,
            parser=XMLParser(collect_ids=False))
    if node.tag == 'datasource':
        nodes = [node]
    else:
        nodes = node.findall(".//datasource")
    dstype = ""
    if nodes:
        dstype = nodes[0].attrib["type"]
    return dstype


def getdssource(xmlstring):
    """ provides source from datasource xml string

    :param xmlstring: datasource xml string
    :type xmlstring: :obj:`str`
    """

    if sys.version_info > (3,):
        node = et.fromstring(
            bytes(xmlstring, "UTF-8"),
            parser=XMLParser(collect_ids=False))
    else:
        node = et.fromstring(
            xmlstring,
            parser=XMLParser(collect_ids=False))
    if node.tag == 'datasource':
        nodes = [node]
    else:
        nodes = node.findall(".//datasource")
    dssource = ""
    if nodes:
        ds = nodes[0]
        dssource = ParserTools.getRecord(ds)
    return dssource


class NXSFileParser(object):

    """ Metadata parser for NeXus files
    """

    def __init__(self, root):
        """ constructor

        :param root: nexus root node
        :type root: :class:`filewriter.FTGroup`
        """

        #: (:obj:`list` <:obj:`dict` <:obj:`str`, `any`> >) \
        #  description list of found nodes
        self.description = []
        #: (:obj:`str`) group postfix
        self.group_postfix = ""
        #: (:obj:`bool`) store NXentries as scientificMetadata
        self.scientific = False
        #: (:obj:`bool`) add empty units
        self.emptyunits = False

        #: (:obj:`list` <:obj:`str` >) \
        #    nexus field attribute show names
        self.attrs = None
        #: (:obj:`list` <:obj:`str` >) \
        #    nexus field attribute hidden names
        self.hiddenattrs = [
            "nexdatas_source",
            "nexdatas_strategy"
        ]
        #: (:obj:`list` <:obj:`str` >) \
        #    nexus entry classes to be shown
        self.entryclasses = [
            "NXentry"
        ]
        #: (:obj:`list` <:obj:`str` >) \
        #    nexus entry names to be shown
        self.entrynames = [
        ]
        #: (:obj:`dict` <:obj:`str`, [:obj:`str, `any`] > >) \
        #  attribute description
        self.attrdesc = {
            "nexus_type": ["type", str],
            "units": ["units", str],
            "depends_on": ["depends_on", str],
            "trans_type": ["transformation_type", str],
            "trans_vector": ["vector", str],
            "trans_offset": ["offset", str],
            "source_name": ["nexdatas_source", getdsname],
            "source_type": ["nexdatas_source", getdstype],
            "source": ["nexdatas_source", getdssource],
            "strategy": ["nexdatas_strategy", str],
        }
        #: (:obj:`dict` <:obj:`str`, [:obj:`str, `any`] > >) \
        #  metadata attribute description
        self.mattrdesc = {
            "source_name": ["nexdatas_source", getdsname],
            "source_type": ["nexdatas_source", getdstype],
            "source": ["nexdatas_source", getdssource],
            "strategy": ["nexdatas_strategy", str],
            "unit": ["units", str],
        }
        #: (:obj:`list`< :obj:`str`>)  field names which value should be stored
        self.valuestostore = ["depends_on"]
        self.__root = root
        #: (:obj:`list`< :obj:`str`>)  filters for `full_path` names
        self.filters = []
        # (:obj:`bool`) oned value flag
        self.oned = False
        # (:obj:`int`) maximal 1d record size
        self.maxonedsize = -1

    @classmethod
    def getpath(cls, path):
        """ converts full_path with NX_classes into nexus_path

        :param path: nexus full_path
        :type path: :obj:`str`
        """
        spath = path.split("/")
        return "/".join(
            [(dr if ":" not in dr else dr.split(":")[0])
             for dr in spath])

    def __addnode(self, node, tgpath):
        """adds the node into the description list

        :param node: nexus node
        :type node: :class:`filewriter.FTField` or \
                    :class:`filewriter.FTLink` or \
                    :class:`filewriter.FTAttribute` or \
                    :class:`filewriter.FTGroup`
        :param tgpath: target path of the link target or `None`
        :type tgpath: :obj:`str`
        """
        desc = {}
        path = filewriter.first(node.path)
        desc["full_path"] = str(path)
        desc["nexus_path"] = str(self.getpath(path))
        if hasattr(node, "dtype"):
            desc["dtype"] = str(node.dtype)
        if hasattr(node, "shape"):
            desc["shape"] = [int(n) for n in (node.shape or [])]
        if hasattr(node, "attributes"):
            attrs = node.attributes
            anames = [at.name for at in attrs]
            for key, vl in self.attrdesc.items():
                if vl[0] in anames:
                    desc[key] = vl[1](filewriter.first(attrs[vl[0]].read()))
        if node.name in self.valuestostore and node.is_valid:
            try:
                vl = node.read()
                cont = True
                while cont:
                    try:
                        if isinstance(vl, np.ndarray) and \
                           vl.shape == ():
                            vl = vl.item()
                            cont = False
                        elif not isinstance(vl, str) and \
                                (hasattr(vl, "__len__") and len(vl) == 1):
                            vl = vl[0]
                        else:
                            cont = False
                    except Exception:
                        cont = False
                desc["value"] = vl
            except Exception:
                pass
        self.description.append(desc)
        if tgpath:
            fname = self.__root.parent.name
            if "%s:/%s" % (fname, desc["nexus_path"]) != tgpath:
                ldesc = dict(desc)
                if tgpath.startswith(fname):
                    tgpath = tgpath[len(fname) + 2:]
                ldesc["nexus_path"] = "\\-> %s" % tgpath
                self.description.append(ldesc)

    def __parsenode(self, node, tgpath=None):
        """parses the node and add it into the description list

        :param node: nexus node
        :type node: :class:`filewriter.FTField` or \
                    :class:`filewriter.FTLink` or \
                    :class:`filewriter.FTAttribute` or \
                    :class:`filewriter.FTGroup`
        :param tgpath: target path of the link target or `None`
        :type tgpath: :obj:`str`
        """
        self.__addnode(node, tgpath)
        names = []
        if isinstance(node, filewriter.FTGroup):
            names = [
                (ch.name,
                 str(ch.target_path) if hasattr(ch, "target_path") else None)
                for ch in filewriter.get_links(node)]
        for nm in names:
            try:
                ch = node.open(nm[0])
                self.__parsenode(ch, nm[1])
#            except Exception:
#                pass
            finally:
                pass

    def __parsemetaentry(self, node, lst):
        """parses the node and add it into the description list

        :param node: nexus node
        :type node: :class:`filewriter.FTField` or \
                    :class:`filewriter.FTLink` or \
                    :class:`filewriter.FTAttribute` or \
                    :class:`filewriter.FTGroup`
        :param lst: metadata list
        :type lst: :obj:`dict` <:obj:`str`, `any`>
        """
        dct = {}
        name = self.__addmeta(node, dct, self.scientific)
        names = []
        if isinstance(node, filewriter.FTGroup):
            names = [
                (ch.name,
                 str(ch.target_path) if hasattr(ch, "target_path") else None)
                for ch in filewriter.get_links(node)]
        for nm in names:
            try:
                if name in dct.keys():
                    gr = dct[name]
                    if not isinstance(gr, dict):
                        nm = name + "_"
                        while nm in dct.keys():
                            nm = nm + "_"
                        dct[nm] = gr
                        gr = dct[name] = {}
                else:
                    gr = dct[name] = {}
                ch = node.open(nm[0])
                self.__parsemeta(ch, gr)
#            except Exception:
#                pass
            finally:
                pass
        lst.append(dct)

    def __parsemeta(self, node, dct):
        """parses the node and add it into the description list

        :param node: nexus node
        :type node: :class:`filewriter.FTField` or \
                    :class:`filewriter.FTLink` or \
                    :class:`filewriter.FTAttribute` or \
                    :class:`filewriter.FTGroup`
        :param dct: metadata dictionary
        :type dct: :obj:`dict` <:obj:`str`, `any`>
        """
        self.__addmeta(node, dct)
        names = []
        if isinstance(node, filewriter.FTGroup):
            names = [
                (ch.name,
                 str(ch.target_path) if hasattr(ch, "target_path") else None)
                for ch in filewriter.get_links(node)]
        for nm in names:
            try:
                name = node.name + self.group_postfix
                if name in dct.keys():
                    gr = dct[name]
                    if not isinstance(gr, dict):
                        nm = name + "_"
                        while nm in dct.keys():
                            nm = nm + "_"
                        dct[nm] = gr
                        gr = dct[name] = {}
                else:
                    gr = dct[name] = {}
                ch = node.open(nm[0])
                self.__parsemeta(ch, gr)
#            except Exception:
#                pass
            finally:
                pass

    def __addmeta(self, node, dct, scientific=False):
        """adds the node into the description list

        :param node: nexus node
        :type node: :class:`filewriter.FTField` or \
                    :class:`filewriter.FTLink` or \
                    :class:`filewriter.FTAttribute` or \
                    :class:`filewriter.FTGroup`
        :param dct: metadata dictionary
        :type dct: :obj:`dict` <:obj:`str`, `any`>
        :param scientific: scientific flag
        :type scientific: :obj:`bool`
        """
        desc = {}
        # path = filewriter.first(node.path)
        # desc["full_path"] = str(path)
        # desc["nexus_path"] = str(self.getpath(path))
        if isinstance(node, filewriter.FTGroup):
            if scientific:
                smname = "scientificMetadata"
                counter = 1
                while smname in dct.keys():
                    counter += 1
                    smname = "scientificMetadata_%s" % counter

                nd = dct[smname] = {"name": node.name}
            else:
                smname = node.name + self.group_postfix

                if smname in dct.keys():
                    nd = dct[smname]
                    if not isinstance(nd, dict):
                        nm = smname + "_"
                        while nm in dct.keys():
                            nm = nm + "_"
                        dct[nm] = nd
                        nd = dct[smname] = {}
                else:
                    nd = dct[smname] = {}
        else:
            smname = node.name
            if smname in dct.keys():
                nd = dct[smname]
                if not isinstance(nd, dict):
                    nm = smname + "_"
                    while nm in dct.keys():
                        nm = nm + "_"
                    dct[nm] = nd
                    nd = dct[smname] = {}
            else:
                nd = dct[smname] = {}
        if hasattr(node, "dtype"):
            desc["dtype"] = str(node.dtype)
        if hasattr(node, "shape"):
            desc["shape"] = [int(n) for n in (node.shape or [])]
        if hasattr(node, "attributes"):
            attrs = node.attributes
            anames = [at.name for at in attrs]
            for key, vl in self.mattrdesc.items():
                if vl[0] in anames and \
                   (self.attrs is None or key in self.attrs) and \
                   (self.hiddenattrs is None or key not in self.hiddenattrs):
                    nd[key] = vl[1](filewriter.first(attrs[vl[0]].read()))

            if self.attrs is not None:
                for at in self.attrs:
                    if at in anames:
                        if at in self.attrs and \
                           at not in self.mattrdesc.keys() and \
                           (self.hiddenattrs is None or
                                at not in self.hiddenattrs):
                            nd[at] = filewriter.first(attrs[at].read())
            else:
                for at in anames:
                    if at not in self.mattrdesc.keys() and \
                       (self.hiddenattrs is None or
                            at not in self.hiddenattrs):
                        nd[at] = filewriter.first(attrs[at].read())
            if self.scientific and "NX_class" in nd.keys() and \
               nd["NX_class"] == "NXentry":
                nd.pop("NX_class")
        if not isinstance(node, filewriter.FTGroup):
            if (node.name in self.valuestostore and node.is_valid) \
               or "shape" not in desc \
               or desc["shape"] in [None, [1], []] \
               or ((self.oned)
                   and len(desc["shape"]) == 1):
                if hasattr(node, "read"):
                    try:
                        vl = node.read()
                        cont = True
                        while cont:
                            try:
                                if isinstance(vl, np.ndarray) and \
                                   vl.shape == ():
                                    vl = vl.item()
                                    cont = False
                                elif not isinstance(vl, str) and \
                                        (hasattr(vl, "__len__") and
                                         len(vl) == 1):
                                    vl = vl[0]
                                else:
                                    cont = False
                            except Exception:
                                cont = False
                        if self.maxonedsize >= 0 and len(desc["shape"]) == 1 \
                           and hasattr(vl, "__len__") and \
                           len(vl) > self.maxonedsize:
                            try:
                                nd["value"] = [min(vl), max(vl)]
                            except Exception:
                                nd["value"] = [vl[0], vl[-1]]
                        else:
                            nd["value"] = vl
                        if self.emptyunits and "unit" not in nd.keys():
                            nd["unit"] = ""
                    except Exception:
                        pass
            if "shape" in desc and desc["shape"] not in [None, [1], []]:
                if "shape" in nd.keys():
                    shp = nd["shape"]
                    nm = "shape" + "_"
                    while nm in nd.keys():
                        nm = nm + "_"
                    nd[nm] = shp
                nd["shape"] = desc["shape"]
        return smname

    def __filter(self):
        """filters description list

        """
        res = []
        if self.filters:
            for elem in self.description:
                fpath = elem['full_path']
                found = False
                for df in self.filters:
                    found = fnmatch.filter([fpath], df)
                    if found:
                        break
                if found:
                    res.append(elem)
            self.description[:] = res

    def parse(self):
        """parses the file and creates the filtered description list

        """
        self.__parsenode(self.__root)
        self.__filter()

    def parseMeta(self):
        """parses the file and creates the filtered description list

        """
        for entry in self.__root:
            nm = entry.name
            at = None
            try:
                if "NX_class" in entry.attributes.names():
                    at = entry.attributes["NX_class"]
            except Exception:
                pass
            if len(self.entryclasses) == 0 or \
               at and (filewriter.first(at.read()) in self.entryclasses):
                if len(self.entrynames) == 0 or \
                   (nm and nm in self.entrynames):
                    self.__parsemetaentry(entry, self.description)


class FIOFileParser(object):

    """ Metadata parser for FIO files
    """

    def __init__(self, root):
        """ constructor

        :param root: fio file content
        :type root: :obj:`str`
        """

        #: (:obj:`list` <:obj:`dict` <:obj:`str`, `any`> >) \
        #  description list of found nodes
        self.description = []
        #: (:obj:`str`) group postfix
        self.group_postfix = ""
        #: (:obj:`dict` <:obj:`str`, `any`>)  metadata dictionary
        self.__dctmetadata = {}
        #: (:obj:`dict` <:obj:`str`, `any`>)  columns dictionary
        self.columns = {}

        # (:obj:`str`) text content of the file
        self.__root = root
        # (:obj:`bool`) oned value flag
        self.oned = False
        # (:obj:`int`) maximal 1d record size
        self.maxonedsize = -1

    def _appendComments(self, lines, meta):
        """append comments

        :param lines: comment fio lines
        :type lines: :obj:`list` <:obj:`str`>
        :param meta: metadata dictionary
        :type meta: :obj:`dict` <:obj:`str`, `any`>
        """
        comments = {}
        counter = 0
        for line in lines:
            if not line.startswith("!"):
                counter += 1
                comments["line_%s" % counter] = line
                if counter == 1:
                    meta["ScanCommand"] = line
            if "Acquisition started at " in line:
                sline = line.split("Acquisition started at ")
                if sline and sline[-1].strip():
                    meta["start_time"] = {
                        "value": isoDate(sline[-1].strip()),
                        "unit": ""
                    }
            elif "Acquisition ended at " in line:
                sline = line.split("Acquisition ended at ")
                if sline and sline[-1].strip():
                    meta["end_time"] = {
                        "value": isoDate(sline[-1].strip()),
                        "unit": ""
                    }
        if comments:
            meta["comments"] = comments

    def _appendParameters(self, lines, meta):
        """append comments

        :param lines: parameter fio lines
        :type lines: :obj:`list` <:obj:`str`>
        :param meta: metadata dictionary
        :type meta: :obj:`dict` <:obj:`str`, `any`>
        """
        params = {}
        for line in lines:
            if not line.startswith("!") and "=" in line:
                sline = line.split("=")
                if len(sline) > 1 and sline[0].strip() and \
                   sline[1].strip():
                    if '@' not in sline[0]:
                        try:
                            params[sline[0].strip().replace(" ", "_")] = \
                                eval(sline[1].strip())
                        except Exception:
                            params[sline[0].strip().replace(" ", "_")] = \
                                str(sline[1].strip())
        for line in lines:
            if not line.startswith("!") and "=" in line:
                sline = line.split("=")
                if len(sline) > 1 and sline[0].strip() and \
                   sline[1].strip():
                    if '@' in sline[0]:
                        field, attr = sline[0].strip().replace(" ", "_"). \
                            split("@")[:2]
                        try:
                            avl = eval(sline[1].strip())
                        except Exception:
                            avl = str(sline[1].strip())

                        if field in params:
                            if not isinstance(params[field], dict):
                                params[field] = {"value": params[field]}
                            if attr in ["unit", "units"]:
                                params[field]["unit"] = avl
                            else:
                                params[field][attr] = avl

        if params:
            meta["parameters"] = params

    def _appendData(self, lines, meta):
        """append comments

        :param lines: data fio lines
        :type lines: :obj:`list` <:obj:`str`>
        :param meta: metadata dictionary
        :type meta: :obj:`dict` <:obj:`str`, `any`>
        """
        self.columns = {}
        data = {}
        for line in lines:
            if line.startswith("Col"):
                sline = line.split(" ")
                name = None
                if len(sline) > 2:
                    try:
                        if sline[1].strip():
                            cid = int(sline[1].strip())
                            if sline[2].strip():
                                name = str(sline[2].strip())
                                self.columns[cid - 1] = [name, []]
                    except Exception:
                        pass
            elif not line.startswith("!"):
                sline = [word.strip() for word in line.split(" ")
                         if word.strip()]
                for wid, word in enumerate(sline):
                    if wid in self.columns.keys():
                        try:
                            self.columns[wid][1].append(float(word))
                        except Exception:
                            self.columns[wid][1].append(str(word))
        for wid, nmvl in self.columns.items():
            if self.maxonedsize >= 0 \
               and hasattr(nmvl[1], "__len__") and \
               len(nmvl[1]) > self.maxonedsize:
                data[nmvl[0]] = [nmvl[1][0], nmvl[1][-1]]
            else:
                data[nmvl[0]] = nmvl[1]
        if data:
            meta["data"] = data

    def parseMeta(self):
        """parses the file and creates the filtered description list

        """
        smname = "scientificMetadata"
        dct = {}
        self.description = [dct]
        nd = dct[smname] = {}
        if self.__root and isinstance(self.__root, str):
            lines = [line.strip() for line in self.__root.split("\n")]
            dcpmap = {"%d": [], "%c": [], "%p": []}
            last = None
            for line in lines:
                if line in dcpmap.keys():
                    last = line
                elif last and not line.startswith("!"):
                    dcpmap[last].append(line)
                elif line.startswith("!"):
                    dcpmap["%c"].append(line)

            if dcpmap["%c"]:
                self._appendComments(dcpmap["%c"], nd)
            if dcpmap["%p"]:
                self._appendParameters(dcpmap["%p"], nd)
            if dcpmap["%d"] and (self.oned):
                self._appendData(dcpmap["%d"], nd)
