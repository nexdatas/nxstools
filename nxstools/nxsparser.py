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
import json
import fnmatch
import xml.etree.ElementTree as et
import lxml.etree
from lxml.etree import XMLParser


if sys.version_info > (3,):
    unicode = str


def _parseString(text):
    if sys.version_info > (3,):
        return et.fromstring(
            bytes(text, "UTF-8"),
            parser=XMLParser(collect_ids=False))
    else:
        return et.fromstring(
            text,
            parser=XMLParser(collect_ids=False))


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


class ESRFConverter(object):
    """ ESRF xml configuration converter """

    def __init__(self):
        """ constructor """

        self.__allowed_tags = [
            "group", "field", "link", "attribute", "doc",
            "strategy", "datasource"]

        self.__amap = {
            "NX_class": "type",
            "groupName": "name",
            "NAPItype": "type",
            "ref": "target"
        }

    def convert(self, text):
        """ converts ESRF xml configuration to nxsdatawriter format

        :param text: input xml string
        :type text: :obj:`str`
        :returns: output xml string
        :rtype: :obj:`str`
        """
        tree = _parseString(text)
        if tree.tag == "definition":
            definition = tree
        else:
            definition = lxml.etree.Element('definition')
            definition.append(tree)
        self._convert(tree)
        return _toxml(definition)

    def _convert(self, tree):
        """ converts ESRF xml etree configuration to nxsdatawriter format

        :param tree: etree Element node
        :type tree: :class:`lxml.etree.Element`
        """
        if tree.tag not in self.__allowed_tags:
            if "name" not in tree.attrib.keys():
                tree.attrib["name"] = tree.tag
                tree.tag = "field"
        for ikey, okey in self.__amap.items():
            if ikey in tree.attrib.keys() \
               and okey not in tree.attrib.keys():
                tree.attrib[okey] = tree.attrib.pop(ikey)
        if 'ESRF_description' in tree.attrib.keys():
            text = tree.attrib.pop('ESRF_description')
            doc = lxml.etree.Element('doc')
            doc.text = text
            tree.append(doc)
        if 'record' in tree.attrib.keys():
            text = tree.attrib.pop('record')
            mode = lxml.etree.Element("strategy")
            mode.attrib["mode"] = text.upper()
            tree.append(mode)
        for tr in tree:
            self._convert(tr)


class ParserTools(object):

    """ configuration server adapter
    """

    @classmethod
    def _getPureText(cls, node):
        """ collects text from text child nodes

        :param node: parent node
        :type node: :obj:`xml.etree.ElementTree.Element`
        """
        if node is not None:
            tnodes = ([node.text] if node.text else []) \
                     + [child.tail for child in node if child.tail]
            return unicode("".join(tnodes)).strip()
        return ""

    @classmethod
    def _getText(cls, node):
        """ provides  xml content of the node

        :param node: DOM node
        :type node: :class:`lxml.etree.Element`
        :returns: xml content string
        :rtype: :obj:`str`
        """
        if not node:
            return
        xmlc = _toxml(node)
        start = xmlc.find('>')
        end = xmlc.rfind('<')
        if start == -1 or end < start:
            return ""
        return xmlc[start + 1:end].replace("&lt;", "<").replace("&gt;", ">"). \
            replace("&quot;", "\"").replace("&amp;", "&")

    @classmethod
    def getRecord(cls, node):
        """ fetches record name or query from datasource node

        :param node: datasource node
        :type node: :class:`lxml.etree.Element`
        :returns: record name or query
        :rtype: :obj:`str`
        """
        withRec = ["CLIENT", "TANGO"]
        withResult = ["PYEVAL"]
        withQuery = ["DB"]
        if node.tag == 'datasource':
            dsource = node
        else:
            dsource = node.find(".//datasource")
        dstype = dsource.attrib["type"]
        res = ''
        if dstype and dstype in withRec:
            host = None
            port = None
            dname = None
            rname = None
            member = None
            device = dsource.findall("device")
            if device is not None and len(device) > 0:
                host = device[0].get("hostname")
                port = device[0].get("port")
                dname = device[0].get("name")
                member = device[0].get("member")
            surfix = ""
            prefix = ""
            if member or member != 'attribute':
                if member == 'property':
                    prefix = '@'
                elif member == 'command':
                    surfix = '()'
            record = dsource.findall("record")
            if record is not None and len(record) > 0:
                rname = record[0].get("name")
                if rname:
                    if dname:
                        if host:
                            if not port:
                                port = '10000'
                            res = '%s:%s/%s/%s%s%s' % (
                                host, port, dname, prefix, rname, surfix)
                        else:
                            res = '%s/%s%s%s' % (dname, prefix, rname, surfix)
                    else:
                        res = rname
                return res
        elif dstype and dstype in withQuery:
            query = dsource.find(".//query")
            if len(query.text) and query.text.strip():
                return query.text.strip() or ""
        elif dstype and dstype in withResult:
            result = dsource.findall("result")
            cresult = dsource.find(".//result")
            if result is not None and len(result) > 0:
                rname = result[0].get("name", "result")
                tres = "ds.%s = " % rname
                if len(cresult.text) and cresult.text.strip():
                    teres = cresult.text.strip() or ""
                    lres = teres.split("\n")
                    for re in lres:
                        if re.strip().startswith(tres):
                            res = re.strip()[len(tres):]
        return res

    @classmethod
    def mergeDefinitions(cls, xmls):
        """ merges the xmls list of definitions xml strings
            to one output xml string

        :param xmls: a list of xml string with definitions
        :type xmls: :obj:`list` <:obj:`str`>
        :returns: one output xml string
        :rtype: :obj:`str`
        """
        rxml = ""
        if xmls:
            indom1 = _parseString(xmls[0])
            for xmlc in xmls[1:]:
                definition = _parseString(xmlc)
                if definition.tag == "definition":
                    definitions = [definition]
                else:
                    definitions = definition.findall("definition")
                for defin in definitions:
                    for tag in defin:
                        indom1.append(tag)
            rxml = _toxml(indom1)
        return rxml

    @classmethod
    def parseDataSources(cls, xmlc):
        """ provides datasources and its records from xml string

        :param xmlc: xml string
        :type xmlc: :obj:`str`
        :returns: list of datasource descriptions
        :rtype: :obj:`list` <:obj:`dict` <:obj:`str`, :obj:`str`>>
        """
        indom = _parseString(xmlc)
        return cls.__getDataSources(indom)

    @classmethod
    def __getDataSources(cls, node, direct=False):
        """ provides datasources and its records from xml string

        :param xmlc: xml string
        :type xmlc: :obj:`str`
        :returns: list of datasource descriptions
        :rtype: :obj:`list` <:obj:`dict` <:obj:`str`, :obj:`str`>>
        """
        dss = []
        if direct:
            dss.extend(node.findall("datasource"))
        else:
            if node.tag == "datasource":
                dss.append(node)
            dss.extend(node.findall(".//datasource"))
        dslist = []
        for ds in dss:
            if ds.tag == 'datasource':
                dstype = ds.attrib["type"]
                dsname = ds.attrib["name"]
                record = cls.getRecord(ds)
                dslist.append({
                    "source_type": dstype,
                    "source_name": dsname,
                    "source": record,
                })

        return dslist

    @classmethod
    def __getPath(cls, node):
        """ provides node path

        :param node: etree node
        :type node: :class:`lxml.etree.Element`
        :returns: node path
        :rtype: :obj:`str`
        """
        name = cls.__getAttr(node, "name")
        if not name:
            return ""
        attr = False
        while node.getparent() is not None:
            onode = node
            node = node.getparent()
            if onode.tag == "attribute":
                attr = True
            else:
                attr = False
            if node.tag not in ["group", "field"]:
                return name
            else:
                gname = cls.__getAttr(node, "name")
                if not gname:
                    gname = cls.__getAttr(node, "type")
                    if len(gname) > 2:
                        gname = gname[2:]
                if attr:
                    name = gname + "@" + name
                else:
                    name = gname + "/" + name
                attr = False
        return name

    @classmethod
    def __getFullPath(cls, node):
        """ provides node path

        :param node: etree node
        :type node: :class:`lxml.etree.Element`
        :returns: node path
        :rtype: :obj:`str`
        """
        name = cls.__getAttr(node, "name")
        if not name:
            return ""
        attr = False
        while node.getparent() is not None:
            onode = node
            node = node.getparent()
            if onode.tag == "attribute":
                attr = True
            else:
                attr = False
            if node.tag not in ["group", "field"]:
                return name
            else:
                gname = cls.__getAttr(node, "name")
                nxtype = cls.__getAttr(node, "type")
                if not gname:
                    if len(nxtype) > 2:
                        gname = nxtype[2:]
                if attr:
                    name = gname + "@" + name
                elif nxtype:
                    name = "%s:%s/%s" % (gname, nxtype, name)
                else:
                    name = gname + "/" + name

                attr = False
        return name

    @classmethod
    def __getAttr(cls, node, name, tag=False):
        """ provides value of attirbute

        :param node: etree node
        :type node: :class:`lxml.etree.Element`
        :returns: attribute value
        :rtype: :obj:`str`
        """
        if name in node.attrib:
            return node.attrib[name]
        elif tag:
            if node.tag == "attribute":
                atnodes = [node]
            else:
                atnodes = []
            atnodes.extend(node.findall("attribute"))
            text = None
            for at in atnodes:
                if cls.__getAttr(at, "name") == name:
                    text = str(cls._getPureText(at)).strip()
                    if not text:
                        dss = cls.__getDataSources(at)
                        text = " ".join(["$datasources.%s" % ds for ds in dss])
            return text
        else:
            return None

    @classmethod
    def __getAllAttr(cls, node, exclude=None):
        """ provides value of attirbute

        :param node: etree node
        :type node: :class:`lxml.etree.Element`
        :returns: attribute dictionary
        :rtype: :obj:<:obj:`str`, :obj:`any`>
        """
        res = {}
        exclude = exclude or []
        for name in node.attrib.keys():
            if name not in exclude:
                res[name] = node.attrib[name]
        return res

    @classmethod
    def __getShape(cls, node):
        """ provides node shape

        :param node: etree node
        :type node: :class:`lxml.etree.Element`
        :returns: shape list
        :rtype: :obj:`list` <:obj:`int`>
        """
        rank = int(node.attrib["rank"])
        #        shape = ['*'] * rank
        shape = [None] * rank
        dims = node.findall("dim")
        for dim in dims:
            index = int(dim.attrib["index"])
            if "value" in dim.attrib:
                try:
                    value = int(dim.attrib["value"])
                except ValueError:
                    value = str(dim.attrib["value"])
                shape[index - 1] = value
            else:
                dss = dim.findall("datasource")
                if dss:
                    value = dss[0].get("name")
                    if not value:
                        value = '__unnamed__'
                    shape[index - 1] = "$datasources.%s" % value
                else:
                    tnodes = " ".join(
                        ([dim.text] if dim.text else []) +
                        [child.tail for child in dim if child.tail])
                    value = ("".join(tnodes)).strip()
                    try:
                        value = int(value)
                    except Exception:
                        value = value.strip()
                        if not value:
                            value = None
                    shape[index - 1] = value

        return shape

    @classmethod
    def __getChildrenByTagName(cls, parent, name):
        """ provides direct children by tag name

        :param parent: parent node
        :type parent: :class:`lxml.etree.Element`
        :param name: tag name
        :type name: :obj:`str`
        :returns: list of children
        :rtype: :obj:`list` <:class:`lxml.etree.Element`>
        """
        return [ch for ch in parent.findall(name) if ch.tag == name]

    @classmethod
    def parseFields(cls, xmlc):
        """ provides datasources and its records from xml string

        :param xmlc: xml string
        :type xmlc: :obj:`str`
        :returns: list of datasource descriptions
        :rtype: :obj:`list` < :obj:`dict` <:obj:`str`, `any`> >
        """
        tagname = "field"
        indom = _parseString(xmlc)
        nodes = []
        if indom.tag == tagname:
            nodes.append(indom)
        nodes.extend(indom.findall(".//%s" % tagname))
        taglist = []
        for nd in nodes:
            if nd.tag == tagname:
                nxtype = cls.__getAttr(nd, "type")
                units = cls.__getAttr(nd, "units")
                value = cls._getPureText(nd) or None
                trtype = cls.__getAttr(nd, "transformation_type", True)
                trvector = cls.__getAttr(nd, "vector", True)
                troffset = cls.__getAttr(nd, "offset", True)
                trdependson = cls.__getAttr(nd, "depends_on", True)
                nxpath = cls.__getPath(nd)
                fullnxpath = cls.__getFullPath(nd)
                dnodes = cls.__getChildrenByTagName(nd, "dimensions")
                shape = cls.__getShape(dnodes[0]) if dnodes else None
                docnodes = cls.__getChildrenByTagName(nd, "doc")
                doc = cls._getPureText((docnodes[0])) if docnodes else None
                stnodes = cls.__getChildrenByTagName(nd, "strategy")
                strategy = cls.__getAttr(stnodes[0], "mode") \
                    if stnodes else None

                sfdinfo = {
                    "strategy": strategy,
                    "nexus_path": nxpath,
                    "full_nexus_path": fullnxpath,
                }
                fdinfo = {
                    "nexus_type": nxtype,
                    "units": units,
                    "shape": shape,
                    "trans_type": trtype,
                    "trans_vector": trvector,
                    "trans_offset": troffset,
                    "depends_on": trdependson,
                    "value": value,
                    "doc": doc
                }
                fdinfo.update(sfdinfo)
                otherinfo = cls.__getAllAttr(nd, list(fdinfo.keys()))
                fdinfo.update(otherinfo)
                dss = cls.__getDataSources(nd, direct=True)
                if dss:
                    for ds in dss:
                        ds.update(fdinfo)
                        taglist.append(ds)
                        nddss = cls.__getChildrenByTagName(nd, "datasource")
                        for ndds in nddss:
                            sdss = cls.__getDataSources(ndds, direct=True)
                            if sdss:
                                for sds in sdss:
                                    sds.update(sfdinfo)
                                    sds["source_name"] \
                                        = "\\" + sds["source_name"]
                                    taglist.append(sds)
                else:
                    taglist.append(fdinfo)

        return taglist

    @classmethod
    def parseAttributes(cls, xmlc):
        """ provides datasources and its records from xml string

        :param xmlc: xml string
        :type xmlc: :obj:`str`
        :returns: list of datasource descriptions
        :rtype: :obj:`list` < :obj:`dict` <:obj:`str`, `any`> >
        """
        tagname = "attribute"
        indom = _parseString(xmlc)
        nodes = []
        if indom.tag == tagname:
            nodes.append(indom)
        nodes.extend(indom.findall(".//%s" % tagname))
        taglist = []
        for nd in nodes:
            if nd.tag == tagname:

                nxtype = cls.__getAttr(nd, "type")
                units = cls.__getAttr(nd, "units")
                value = cls._getPureText(nd) or None
                trtype = cls.__getAttr(nd, "transformation_type", True)
                trvector = cls.__getAttr(nd, "vector", True)
                troffset = cls.__getAttr(nd, "offset", True)
                trdependson = cls.__getAttr(nd, "depends_on", True)
                nxpath = cls.__getPath(nd)
                fullnxpath = cls.__getFullPath(nd)
                dnodes = cls.__getChildrenByTagName(nd, "dimensions")
                shape = cls.__getShape(dnodes[0]) if dnodes else None
                stnodes = cls.__getChildrenByTagName(nd, "strategy")
                strategy = cls.__getAttr(stnodes[0], "mode") \
                    if stnodes else None
                sfdinfo = {
                    "strategy": strategy,
                    "nexus_path": nxpath,
                    "full_nexus_path": fullnxpath,
                }
                fdinfo = {
                    "nexus_type": nxtype,
                    "units": units,
                    "shape": shape,
                    "trans_type": trtype,
                    "trans_vector": trvector,
                    "trans_offset": troffset,
                    "depends_on": trdependson,
                    "value": value
                }
                fdinfo.update(sfdinfo)
                dss = cls.__getDataSources(nd, direct=True)
                if dss:
                    for ds in dss:
                        ds.update(fdinfo)
                        taglist.append(ds)
                        nddss = cls.__getChildrenByTagName(nd, "datasource")
                        for ndds in nddss:
                            sdss = cls.__getDataSources(ndds, direct=True)
                            if sdss:
                                for sds in sdss:
                                    sds.update(sfdinfo)
                                    sds["source_name"] \
                                        = "\\" + sds["source_name"]
                                    taglist.append(sds)
                else:
                    taglist.append(fdinfo)

        return taglist

    @classmethod
    def parseLinks(cls, xmlc):
        """ provides datasources and its records from xml string

        :param xmlc: xml string
        :type xmlc: :obj:`str`
        :returns: list of datasource descriptions
        :rtype: :obj:`list` < :obj:`dict` <:obj:`str`, `any`> >
        """
        tagname = "link"
        indom = _parseString(xmlc)
        nodes = []
        if indom.tag == tagname:
            nodes.append(indom)
        nodes.extend(indom.findall(".//%s" % tagname))
        taglist = []
        for nd in nodes:
            if nd.tag == tagname:

                target = cls.__getAttr(nd, "target")
                value = cls._getPureText(nd) or None
                nxpath = cls.__getPath(nd)
                stnodes = cls.__getChildrenByTagName(nd, "strategy")
                strategy = cls.__getAttr(stnodes[0], "mode") \
                    if stnodes else None

                sfdinfo = {
                    "strategy": strategy,
                    "nexus_path": "[%s]" % nxpath,
                }
                fdinfo = {
                    "value": value
                }
                fdinfo.update(sfdinfo)
                dss = cls.__getDataSources(nd, direct=True)
                if dss:
                    for ds in dss:
                        ds.update(fdinfo)
                        taglist.append(ds)
                        nddss = cls.__getChildrenByTagName(nd, "datasource")
                        for ndds in nddss:
                            sdss = cls.__getDataSources(ndds, direct=True)
                            if sdss:
                                for sds in sdss:
                                    sds.update(sfdinfo)
                                    sds["source_name"] \
                                        = "\\" + sds["source_name"]
                                    taglist.append(sds)
                else:
                    taglist.append(fdinfo)
                    if target and target.strip():
                        fdinfo2 = dict(fdinfo)
                        fdinfo2["nexus_path"] = "\\-> %s" % target
                        taglist.append(fdinfo2)

        return taglist

    @classmethod
    def parseRecord(cls, xmlc):
        """ provides source record from xml string

        :param xmlc: xml string
        :type xmlc: :obj:`str`
        :returns: source record
        :rtype: :obj:`str`
        """
        indom = _parseString(xmlc)
        return cls.getRecord(indom)


class TableTools(object):

    """ configuration server adapter
    """

    def __init__(self, description, nonone=None, headers=None, filters=None):
        """ constructor

        :param description: description list
        :type description:  :obj:`list` <:obj:`str`>
        :param nonone: list of parameters which have to exist to be shown
        :type nonone:  :obj:`list` <:obj:`str`>
        :param headers: list of output parameters
        :type headers: :obj:`list` <:obj:`str`>
        :param filters:  filters for first column names
        :type filters: :obj:`list` <:obj:`str`>
        """
        #: (:obj:`list` <:obj:`str`>)
        #:    list of parameters which have to exist to be shown
        self.__nonone = nonone or []
        #: (:obj:`list` <:obj:`str`>)
        #:    description list
        self.__description = []
        #: (:obj:`dict` <:obj:`str` , :obj:`int`>) header sizes
        self.__hdsizes = {}
        #: (:obj:`list` <:obj:`str`>) table headers
        self.headers = [
            'nexus_path',
            'nexus_type',
            'strategy',
            'shape',
            'units',
            'depends_on',
            'trans_type',
            'trans_vector',
            'trans_offset',
            'source_name',
            'source_type',
            'source',
            'value'
        ]
        #: (:obj:`list` <:obj:`str`>) filter list
        self.filters = []
        if headers:
            self.headers = headers
        if filters:
            self.filters = filters

        #: (:obj:`str`) table title
        self.title = None
        self.loadDescription(description)

    def loadDescription(self, description):
        """ loads description

        :param description:  description list
        :type description:  :obj:`list` <:obj:`str`>
        """
        if self.headers:
            hkey = self.headers[0]
        for desc in description:
            if desc is None:
                self.__description.append(desc)
                continue
            skip = False
            found = False
            field = desc.get("nexus_path", "").split('/')[-1]
            value = desc.get("value", "")
            if field == 'depends_on' and value:
                desc["depends_on"] = "[%s]" % value
            for hd in self.__nonone:
                vl = desc.get(hd, "")
                if isinstance(vl, (list, tuple)):
                    vl = self.__toString(vl)
                if not vl:
                    skip = True
                    break
            if self.filters and hkey in desc.keys():
                vl = desc[hkey]
                found = False
                for df in self.filters:
                    found = fnmatch.filter([vl], df)
                    if found:
                        break
                if not found:
                    skip = True
                    continue
            elif not self.filters:
                found = True
            if not skip and found:
                self.__description.append(desc)
        for desc in self.__description:
            if desc is None:
                continue
            for hd, vl in desc.items():
                if hd not in self.__nonone or vl:
                    if hd not in self.__hdsizes.keys():
                        self.__hdsizes[hd] = max(len(hd) + 1, 5)
                    if isinstance(vl, (list, tuple)):
                        vl = self.__toString(vl)
                    if not isinstance(vl, str):
                        vl = str(vl)
                    if self.__hdsizes[hd] <= len(vl):
                        self.__hdsizes[hd] = len(vl) + 1

    @classmethod
    def __toString(cls, lst):
        """ converts list to string

        :param lst: given list
        :type lst: :obj:`list` <:obj:`str`>
        :returns: list in string representation
        :rtype: :obj:`str`
        """
        res = []
        for it in lst:
            res.append(it or "*")
        return str(res)

    def generateList(self):
        """ generate row lists of table

        :returns:  table rows
        :rtype: :obj:`list` <:obj:`str`>
        """
        lst = [""]
        if self.title is not None:
            lst.append(self.title)
            lst.append("-" * len(self.title))
            lst.append("")

        headers = [hd for hd in self.headers if hd in self.__hdsizes.keys()]
        line = ""
        for hd in headers:
            line += "=" * (self.__hdsizes[hd] - 1) + " "
        lst.append(line)

        line = ""
        for hd in headers:
            line += hd + " " * (self.__hdsizes[hd] - len(hd))
        lst.append(line)

        line = ""
        for hd in headers:
            line += "=" * (self.__hdsizes[hd] - 1) + " "
        lst.append(line)

        for desc in self.__description:
            line = ""
            if desc is None:
                for hd in headers:
                    line += "=" * (self.__hdsizes[hd] - 1) + " "
                lst.append(line.rstrip())
                continue
            line = ""
            for hd in headers:
                vl = desc[hd] if hd in desc else None
                if isinstance(vl, (list, tuple)):
                    vl = self.__toString(vl)
                elif vl is None:
                    vl = ""
                elif not isinstance(vl, str):
                    vl = str(vl)
                line += vl + " " * (self.__hdsizes[hd] - len(vl))

            lst.append(line.rstrip())

        line = ""
        for hd in headers:
            line += "=" * (self.__hdsizes[hd] - 1) + " "
        lst.append(line)

        lst.append("")

        return lst


class TableDictTools(object):

    """ configuration server adapter
    """

    def __init__(self, description, nonone=None):
        """ constructor

        :param description: description list
        :type description:  :obj:`list` <:obj:`str`>
        :param nonone: list of parameters which have to exist to be shown
        :type nonone:  :obj:`list` <:obj:`str`>
        """
        #: (:obj:`list` <:obj:`str`>)
        #:    description list
        self.__description = description

        #: (:obj:`list` <:obj:`str`>)
        #:    headers
        self.headers = [
            'Timer',
            'DataSourceSelection',
            'ComponentSelection',
            'ComponentPreselection',
            'DataSourcePreselection',

            'UserData',
            'AppendEntry',
            'ConfigDevice',
            'WriterDevice',
            'Door',

            'DynamicComponents',
            'ComponentsFromMntGrp',
            'DefaultDynamicLinks',
            'DefaultDynamicPath',
            'UnplottedComponents',
            'OptionalComponents',
            'ConfigVariables',

            # 'TimeZone',
            # 'Version',
            # 'OrderedChannels',
            # 'PreselectingDataSources',
            # 'MntGrpConfiguration',
            # 'ChannelProperties',
            # 'MntGrp',
        ]

        self.headertypenames = {
            'MntGrp': ('str', None),
            'Timer': ('list', 'Timer(s)'),
            'ComponentSelection':
            ('tdict', 'Detector Components'),
            'DataSourceSelection': (
                'tdict', 'Pool/Dynamic Detector Components'),
            'ComponentPreselection': (
                'tdict', 'Descriptive Components'),
            'DataSourcePreselection': (
                'tdict', 'Descriptive Dynamic Components'),
            'UserData': ('dict', 'User Data'),
            'AppendEntry': ('str', None),
            'ConfigDevice': ('str', None),
            'WriterDevice': ('str', None),
            'UnplottedComponents': ('list', 'Unplotted Components'),
            'MntGrpConfiguration': ('str', None),
            'Version': ('str', None),
            'TimeZone': ('str', None),
            'Door': ('str', None),
            'DynamicComponents': ('str', None),
            'PreselectingDataSources': ('list', None),
            'OrderedChannels': ('list', None),
            'DefaultDynamicLinks': ('str', None),
            'ConfigVariables': ('str', None),
            'ComponentsFromMntGrp': ('str', None),
            'ChannelProperties': ('str', None),
            'OptionalComponents': ('list', None),
            'DefaultDynamicPath': ('str', None),
        }
        self.orderpar = 'OrderedChannels'
        self.__order = []

        self.typemethods = {
            'str': self._getstr,
            'list': self._getlist,
            'tdict': self._gettdict,
            'dict': self._getdict,
        }

        #: (:obj:`str`) table title
        self.title = None
        self.maxnamesize = max(
            [len(hd) for hd in self.headers] +
            [len(self.headertypenames[hd][1])
             for hd in self.headers
             if self.headertypenames[hd][1]]
        )

    def _getstr(self, name, value):
        space = " " * (self.maxnamesize - len(name))
        sep = ":" if name != " " else name
        return ["%s%s %s%s" % (name, sep, space, value)]

    def _getlist(self, name, value):
        space = " " * (self.maxnamesize - len(name))
        svalue = ", ".join(json.loads(value)) if value else ""
        sep = ":" if name != " " else name
        return ["%s%s %s%s" % (name, sep, space, svalue)]

    def _gettdict(self, name, value):
        space = " " * (self.maxnamesize - len(name))
        dvl = json.loads(value)
        svalue = ""
        if dvl:
            lst = [key for key in dvl.keys() if dvl[key]]
            if self.__order:
                lst1 = [el for el in self.__order if el in lst]
                lst1.extend(sorted(list(set(lst) - set(lst1))))
                lst = lst1
            else:
                lst = sorted(lst)
            svalue = ", ".join(lst)
        sep = ":" if name != " " else name
        return ["%s%s %s%s" % (name, sep, space, svalue)]

    def _getdict(self, name, value):
        space = " " * (self.maxnamesize - len(name))
        sep = ":" if name != " " else name
        return ["%s%s %s%s" % (name, sep, space, value)]

    @classmethod
    def __toString(cls, lst):
        """ converts list to string

        :param lst: given list
        :type lst: :obj:`list` <:obj:`str`>
        :returns: list in string representation
        :rtype: :obj:`str`
        """
        res = []
        for it in lst:
            res.append(it or "*")
        return str(res)

    def generateList(self):
        """ generate row lists of table

        :returns:  table rows
        :rtype: :obj:`list` <:obj:`str`>
        """
        self.maxnamesize = max(
            [len(hd) for hd in self.headers] +
            [len(self.headertypenames[hd][1])
             for hd in self.headers
             if self.headertypenames[hd][1]]
        )
        lst = [""]

        if self.title is not None:
            lst.append(self.title)
            lst.append("-" * len(self.title))
            lst.append("")
        tb = len(lst)
        lst.append("")
        for desc in self.__description:
            if self.orderpar in desc.keys():
                self.__order = json.loads(desc[self.orderpar])
            else:
                self.__order = []
            for hd in self.headers:
                if hd in desc.keys():
                    htp, name = self.headertypenames[hd]
                    method = self.typemethods[htp]
                    lst.extend(method(name or hd, desc[hd]))

        maxsize = max(len(el) for el in lst)
        lst.append(
            "=" * (self.maxnamesize + 1) + " " +
            "=" * (maxsize - 2 - self.maxnamesize))
        lst[tb] = lst[-1]
        return lst
