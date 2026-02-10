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

"""  Creator of XML configuration files """


try:
    import tango
except Exception:
    import PyTango as tango
import sys

import lxml.etree


if sys.version_info > (3,):
    unicode = str


def _tostr(text):
    """ convert bytestr or unicode to python str
    :param text: text to convert
    :type text: :obj:`bytes` or :obj:`unicode` or :obj:`str`
    :returns: converted text
    :rtype: :obj:`str`
    """
    if isinstance(text, str):
        return text
    else:
        if sys.version_info > (3,) and \
           (isinstance(text, bytes) or isinstance(text, unicode)):
            return str(text, "utf-8")
        else:
            return str(text)


class NTag(object):

    """ tag wrapper
    """

    #

    def __init__(self, parent, tagName, nameAttr="", typeAttr=""):
        """ constructor

        :param parent: parent tag element
        :type parent: :class:`NTag`
        :param tagName: tag name
        :type tagName: :obj:`str`
        :param nameAttr: value of name attribute
        :type nameAttr: :obj:`str`
        :param typeAttr: value of type attribute
        :type typeAttr: :obj:`str`
        """

        #: (:class:`lxml.etree.Element`) tag element from etree
        self.elem = lxml.etree.Element(tagName)
        parent.elem.append(self.elem)

        if nameAttr != "":
            self.elem.attrib["name"] = nameAttr
        if typeAttr != "":
            self.elem.attrib["type"] = typeAttr

    def addTagAttr(self, name, value):
        """ adds tag attribute

        :param name: attribute name
        :type name: :obj:`str`
        :param value: attribute value
        :type value: :obj:`str`
        """
        self.elem.attrib[name] = value

    def setText(self, text):
        """ sets tag content

        :param text: tag content
        :type text: :obj:`str`
        """
        self.elem.text = text

    def addText(self, text):
        """ adds tag content

        :param text: tag content
        :type text: :obj:`str`
        """
        self.elem.text = self.elem.text + text


class NAttr(NTag):

    """ Attribute tag wrapper
    """

    def __init__(self, parent, nameAttr, typeAttr=""):
        """ constructor

        :param parent: parent tag element
        :type parent: :class:`NTag`
        :param nameAttr: name attribute
        :type nameAttr: :obj:`str`
        :param typeAttr: type attribute
        :type typeAttr: :obj:`str`
        """
        NTag.__init__(self, parent, "attribute", nameAttr, typeAttr)

    def setStrategy(self, mode="STEP", trigger=None, value=None, canfail=None):
        """ sets the attribute strategy

        :param mode: mode data writing, i.e. INIT, STEP, FINAL, POSTRUN
        :type mode: :obj:`str`
        :param trigger: for asynchronous writting,
                        e.g. with different subentries
        :type trigger: :obj:`str`
        :param value: label for postrun mode
        :type value: :obj:`str`
        :param canfail: can fail strategy flag
        :type canfail: :obj:`bool`
        """
        #: strategy of data writing, i.e. INIT, STEP, FINAL, POSTRUN
        strategy = NTag(self, "strategy")
        if strategy:
            strategy.addTagAttr("mode", mode)
        if trigger:
            strategy.addTagAttr("trigger", trigger)
        if canfail:
            strategy.addTagAttr("canfail", "true")
        if value:
            strategy.setText(value)


class NGroup(NTag):

    """ Group tag wrapper
    """

    def __init__(self, parent, nameAttr, typeAttr=""):
        """ constructor

        :param parent: parent tag element
        :type parent: :class:`NTag`
        :param nameAttr: name attribute
        :type nameAttr: :obj:`str`
        :param typeAttr: type attribute
        :type typeAttr: :obj:`str`
        """
        NTag.__init__(self, parent, "group", nameAttr, typeAttr)
        #: (:obj:`list` <:obj:`str`> ) list of doc tag contents
        self._doc = []
        #: (:obj:`dict` <:obj:`str` , :obj:`str`> )
        #:    container with attribute tag wrappers
        self._gAttr = {}

    def addDoc(self, doc):
        """ adds doc tag content

        :param doc: doc tag content
        :type doc: :obj:`str`
        """
        self._doc.append(NTag(self, "doc"))
        self._doc[-1].addText(doc)

    def addAttr(self, attrName, attrType, attrValue=""):
        """adds attribute: tag

        :param attrName: name attribute
        :type attrName: :obj:`str`
        :param attrType: type attribute
        :type attrType: :obj:`str`
        :param attrValue: content of the attribute tag
        :type attrValue: :obj:`str`
        """
        print("%s %s %s" % (attrName, attrType, attrValue))
        at = NAttr(self, attrName, attrType)
        self._gAttr[attrName] = at
        if attrValue != "":
            at.setText(attrValue)
        return self._gAttr[attrName]


class NLink(NTag):

    """ Link tag wrapper
    """

    def __init__(self, parent, nameAttr, gTarget):
        """ constructor

        :param parent: parent tag element
        :type parent: :class:`NTag`
        :param nameAttr: name attribute
        :type nameAttr: :obj:`str`
        :param gTarget: target attribute
        :type gTarget: :obj:`str`
        """
        NTag.__init__(self, parent, "link", nameAttr)
        self.addTagAttr("target", gTarget)
        #: list of doc tag contents
        self._doc = []

    def addDoc(self, doc):
        """ adds doc tag content

        :param doc: doc tag content
        :type doc: :obj:`str`
        """
        self._doc.append(NTag(self, "doc"))
        self._doc[-1].addText(doc)


class NDimensions(NTag):

    """ Dimensions tag wrapper
    """

    def __init__(self, parent, rankAttr):
        """ constructor

        :param parent: parent tag element
        :type parent: :class:`NTag`
        :param rankAttr: rank attribute
        :type rankAttr: :obj:`str`
        """
        NTag.__init__(self, parent, "dimensions")
        self.addTagAttr("rank", rankAttr)
        #: (:obj:`dict` <:obj:`str`, :class:`NDim`>)
        #:    container with dim tag wrapper
        self.dims = {}

    def dim(self, indexAttr, valueAttr):
        """ adds dim tag

        :param indexAttr: index attribute
        :type indexAttr: :obj:`str`
        :param valueAttr: value attribute
        :type valueAttr: :obj:`str`
        """
        self.dims[indexAttr] = NDim(self, indexAttr, valueAttr)


class NDim(NTag):

    """ Dim tag wrapper
    """

    def __init__(self, parent, indexAttr, valueAttr):
        """ constructor

        :param parent: parent tag element
        :type parent: :class:`NTag`
        :param indexAttr: index attribute
        :type indexAttr: :obj:`str`
        :param valueAttr: value attribute
        :type valueAttr: :obj:`str`
        """
        NTag.__init__(self, parent, "dim")
        self.addTagAttr("index", indexAttr)
        self.addTagAttr("value", valueAttr)


class NField(NTag):

    """ Field tag wrapper
    """

    def __init__(self, parent, nameAttr, typeAttr=""):
        """constructor

        :param parent: parent tag element
        :type parent: :class:`NTag`
        :param nameAttr: name attribute
        :type nameAttr: :obj:`str`
        :param typeAttr: type attribute
        :type typeAttr: :obj:`str`
        """
        NTag.__init__(self, parent, "field", nameAttr, typeAttr)

        #: (:obj:`list` <:obj:`str`> ) list of doc tag contents
        self._doc = []
        #: (:obj:`dict` <:obj:`str` , :obj:`str`> )
        #:    container with attribute tag wrappers
        self._attr = {}

    def setStrategy(self, mode="STEP", trigger=None, value=None,
                    grows=None, compression=False, rate=None,
                    shuffle=None, canfail=None, compression_opts=None):
        """ sets the field strategy

        :param mode: mode data writing, i.e. INIT, STEP, FINAL, POSTRUN
        :type mode: :obj:`str`
        :param trigger: for asynchronous writting,
                        e.g. with different subentries
        :type trigger: :obj:`str`
        :param value: label for postrun mode
        :type value: :obj:`str`
        :param grows: growing dimension
        :type grows: :obj:`str`
        :param compression: flag if compression shuold be applied
        :type compression: :obj:`str`
        :param rate: compression rate
        :type rate: :obj:`str`
        :param shuffle: flag if compression shuffle
        :type shuffle: :obj:`str`
        :param canfail: can fail strategy flag
        :type canfail: :obj:`bool`
        """
        #: strategy of data writing, i.e. INIT, STEP, FINAL, POSTRUN
        strategy = NTag(self, "strategy")
        if strategy:
            strategy.addTagAttr("mode", mode)
        if grows:
            strategy.addTagAttr("grows", grows)
        if trigger:
            strategy.addTagAttr("trigger", trigger)
        if value:
            strategy.setText(value)
        if canfail:
            strategy.addTagAttr("canfail", "true")
        if compression:
            if int(compression) == 1:
                strategy.addTagAttr("compression", "true")
                if rate is not None:
                    strategy.addTagAttr("rate", str(rate))
            else:
                strategy.addTagAttr(
                    "compression", int(compression))
                if compression_opts:
                    strategy.addTagAttr(
                        "compression_opts",
                        ",".join([str(opts) for opts in compression_opts]))
            if shuffle is not None:
                strategy.addTagAttr(
                    "shuffle",
                    "true" if shuffle else "false")

    def setUnits(self, unitsAttr):
        """ sets the field unit

        :param unitsAttr: the field unit
        :type unitsAttr: :obj:`str`
        """
        self.addTagAttr("units", unitsAttr)

    def addDoc(self, doc):
        """ adds doc tag content

        :param doc: doc tag content
        :type doc: :obj:`str`
        """
        self._doc.append(NTag(self, "doc"))
        self._doc[-1].addText(doc)

    def addAttr(self, attrName, attrType, attrValue=""):
        """ adds attribute tag

        :param attrName: name attribute
        :type attrName: :obj:`str`
        :param attrType: type attribute
        :type attrType: :obj:`str`
        :param attrValue: content of the attribute tag
        :type attrValue: :obj:`str`
        """
        self._attr[attrName] = NAttr(self, attrName, attrType)
        if attrValue != '':
            self._attr[attrName].setText(attrValue)
        return self._attr[attrName]


class NDSource(NTag):

    """ Source tag wrapper
    """

    def __init__(self, parent):
        """ constructor

        :param parent: parent tag element
        :type parent: :class:`NTag`
        """
        NTag.__init__(self, parent, "datasource")

        #: list of doc tag contents
        self._doc = []

    def initDBase(self, name, dbtype, query, dbname=None, rank=None,
                  mycnf=None, user=None,
                  passwd=None, dsn=None, mode=None, host=None, port=None):
        """ sets parameters of DataBase

        :param name: name of datasource
        :type name: :obj:`str`
        :param dbname: name of used DataBase
        :type dbname: :obj:`str`
        :param query: database query
        :type query: :obj:`str`
        :param dbtype: type of the database, i.e. MYSQL, PGSQL, ORACLE
        :type dbtype: :obj:`str`
        :param rank: rank of the query output, i.e. SCALAR, SPECTRUM, IMAGE
        :type rank: :obj:`str`
        :param mycnf: MYSQL config file
        :type mycnf: :obj:`str`
        :param user: database user name
        :type user: :obj:`str`
        :param passwd: database user password
        :type passwd: :obj:`str`
        :param dsn: DSN string to initialize ORACLE and PGSQL databases
        :type dsn: :obj:`str`
        :param mode: mode for ORACLE databases, i.e. SYSDBA or SYSOPER
        :type mode: :obj:`str`
        :param host: name of the host
        :type host: :obj:`str`
        :param port: port number
        :type port: :obj:`str`
        """
        self.addTagAttr("type", "DB")
        self.addTagAttr("name", name)
        da = NTag(self, "database")
        da.addTagAttr("dbtype", dbtype)

        if host:
            da.addTagAttr("hostname", host)
        if port:
            da.addTagAttr("port", port)
        if dbname:
            da.addTagAttr("dbname", dbname)
        if user:
            da.addTagAttr("user", user)
        if passwd:
            da.addTagAttr("passwd", passwd)
        if mycnf:
            da.addTagAttr("mycnf", mycnf)
        if mode:
            da.addTagAttr("mode", mode)
        if dsn:
            da.addText(dsn)

        da = NTag(self, "query")
        if rank:
            da.addTagAttr("format", rank)
        da.addText(query)

    def initTango(self, name, device, memberType, recordName, host=None,
                  port=None, encoding=None, group=None):
        """ sets paramters for Tango device

        :param name: name of datasource
        :type name: :obj:`str`
        :param device: device name
        :type device: :obj:`str`
        :param memberType: type of the data object, i.e. attribute,
                           property, command
        :type memberType: :obj:`str`
        :param recordName: name of the data object
        :type recordName: :obj:`str`
        :param host: host name
        :type host: :obj:`str`
        :param port: port
        :type port: :obj:`str`
        :param encoding: encoding of DevEncoded data
        :type encoding: :obj:`str`
        """
        self.addTagAttr("type", "TANGO")
        self.addTagAttr("name", name)
        dv = NTag(self, "device")
        dv.addTagAttr("name", device)

        if memberType:
            dv.addTagAttr("member", memberType)
        if host:
            dv.addTagAttr("hostname", host)
        if port:
            dv.addTagAttr("port", port)
        if encoding:
            dv.addTagAttr("encoding", encoding)
        if group:
            dv.addTagAttr("group", group)

        da = NTag(self, "record")
        da.addTagAttr("name", recordName)

    def initClient(self, name, recordName):
        """ sets paramters for Client data

        :param name: name of datasource
        :type name: :obj:`str`
        :param recordName: name of the data object
        :type recordName: :obj:`str`
        """
        self.addTagAttr("type", "CLIENT")
        self.addTagAttr("name", name)
        da = NTag(self, "record")
        da.addTagAttr("name", recordName)

    def addDoc(self, doc):
        """ adds doc tag content

        :param doc: doc tag content
        :type doc: :obj:`str`
        """
        self._doc.append(NTag(self, "doc"))
        self._doc[-1].addText(doc)


class NDeviceGroup(NGroup):

    """ Tango device tag creator
    """

    #: (:obj:`list` < :obj:`str`>) Tango types
    tTypes = ["DevVoid",
              "DevBoolean",
              "DevShort",
              "DevLong",
              "DevFloat",
              "DevDouble",
              "DevUShort",
              "DevULong",
              "DevString",
              "DevVarCharArray",
              "DevVarShortArray",
              "DevVarLongArray",
              "DevVarFloatArray",
              "DevVarDoubleArray",
              "DevVarUShortArray",
              "DevVarULongArray",
              "DevVarStringArray",
              "DevVarLongStringArray",
              "DevVarDoubleStringArray",
              "DevState",
              "ConstDevString",
              "DevVarBooleanArray",
              "DevUChar",
              "DevLong64",
              "DevULong64",
              "DevVarLong64Array",
              "DevVarULong64Array",
              "DevInt",
              "DevEncoded"]

    #: (:obj:`list` <:obj:`str`>) NeXuS types corresponding to the Tango types
    nTypes = ["NX_CHAR",
              "NX_BOOLEAN",
              "NX_INT32",
              "NX_INT32",
              "NX_FLOAT32",
              "NX_FLOAT64",
              "NX_UINT32",
              "NX_UINT32",
              "NX_CHAR",
              "NX_CHAR",
              "NX_INT32",
              "NX_INT32",
              "NX_FLOAT32",
              "NX_FLOAT64",
              "NX_UINT32",
              "NX_UINT32",
              "NX_CHAR",
              "NX_CHAR",
              "NX_CHAR",
              "NX_CHAR",
              "NX_CHAR",
              "NX_BOOLEAN",
              "NX_CHAR",
              "NX_INT64",
              "NX_UINT64",
              "NX_INT64",
              "NX_UINT64",
              "NX_INT32",
              "NX_CHAR"]

    def __init__(self, parent, deviceName, nameAttr, typeAttr="",
                 commands=True, blackAttrs=None):
        """ constructor

        :param parent: parent tag element
        :type parent: :class:`NTag`
        :param deviceName: tango device name
        :type deviceName: :obj:`str`
        :param nameAttr: name attribute
        :type nameAttr: :obj:`str`
        :param typeAttr: type attribute
        :type typeAttr: :obj:`str`
        :param commands: if we call the commands
        :type commands: :obj:`bool`
        :param blackAttrs: list of excluded attributes
        :type blackAttrs: :obj:`list` <:obj:`str`>
        """
        NGroup.__init__(self, parent, nameAttr, typeAttr)
        #: (:class:`tango.DeviceProxy`) device proxy
        self._proxy = tango.DeviceProxy(deviceName)
        #: (:obj:`dict` <:obj:`str`, :class:`NTag`>) fields of the device
        self._fields = {}
        #: (:obj:`list` <:obj:`str`>) blacklist for Attributes
        self._blackAttrs = blackAttrs if blackAttrs else []
        #: (:obj:`str`) the device name
        self._deviceName = deviceName

        self._fetchProperties()
        self._fetchAttributes()
        if commands:
            self._fetchCommands()

    def _fetchProperties(self):
        """ fetches properties

        :brief: It collects the device properties
        """
        prop = self._proxy.get_property_list('*')
        print("PROPERIES %s" % prop)
        for pr in prop:
            self.addAttr(pr, "NX_CHAR",
                         str(self._proxy.get_property(pr)[pr][0]))
            if pr not in self._fields:
                self._fields[pr] = NField(self, pr, "NX_CHAR")
                self._fields[pr].setStrategy("STEP")
                sr = NDSource(self._fields[pr])
                sr.initTango(
                    self._deviceName, self._deviceName, "property",
                    pr, host="haso228k.desy.de", port="10000")

    def _fetchAttributes(self):
        """ fetches Attributes

        :brief: collects the device attributes
        """

        #: device attirbutes
        attr = self._proxy.get_attribute_list()
        for at in attr:

            print(at)
            cf = self._proxy.attribute_query(at)
            print("QUERY")
            print(cf)
            print(cf.name)
            print(cf.data_format)
            print(cf.standard_unit)
            print(cf.display_unit)
            print(cf.unit)
            print(self.tTypes[cf.data_type])
            print(self.nTypes[cf.data_type])
            print(cf.data_type)

            if at not in self._fields and at not in self._blackAttrs:
                self._fields[at] = NField(self, at, self.nTypes[cf.data_type])
                encoding = None
                if str(cf.data_format).split('.')[-1] == "SPECTRUM":
                    da = self._proxy.read_attribute(at)
                    d = NDimensions(self._fields[at], "1")
                    d.dim("1", str(da.dim_x))
                    if str(da.type) == 'DevEncoded':
                        encoding = 'VDEO'
                if str(cf.data_format).split('.')[-1] == "IMAGE":
                    da = self._proxy.read_attribute(at)
                    d = NDimensions(self._fields[at], "2")
                    d.dim("1", str(da.dim_x))
                    d.dim("2", str(da.dim_y))
                    if str(da.type) == 'DevEncoded':
                        encoding = 'VDEO'

                if cf.unit != 'No unit':
                    self._fields[at].setUnits(cf.unit)
                    self._fields[at].setUnits(cf.unit)

                if cf.description != 'No description':
                    self._fields[at].addDoc(cf.description)
                self.addAttr('URL', "NX_CHAR", "tango://" + self._deviceName)

                self._fields[at].setStrategy("STEP")
                sr = NDSource(self._fields[at])
                sr.initTango(self._deviceName, self._deviceName, "attribute",
                             at, host="haso228k.desy.de", port="10000",
                             encoding=encoding)

    def _fetchCommands(self):
        """ fetches commands

        :brief: It collects results of the device commands
        """
        #: list of the device commands
        cmd = self._proxy.command_list_query()
        print("COMMANDS %s" % cmd)
        for cd in cmd:
            if str(cd.in_type).split(".")[-1] == "DevVoid" \
                    and str(cd.out_type).split(".")[-1] != "DevVoid" \
                    and str(cd.out_type).split(".")[-1] in self.tTypes \
                    and cd.cmd_name not in self._fields:
                self._fields[cd.cmd_name] = \
                    NField(
                        self, cd.cmd_name,
                        self.nTypes[self.tTypes.index(
                            str(cd.out_type).split(".")[-1])])
                self._fields[cd.cmd_name].setStrategy("STEP")
                sr = NDSource(self._fields[cd.cmd_name])
                sr.initTango(self._deviceName, self._deviceName,
                             "command", cd.cmd_name,
                             host="haso228k.desy.de", port="10000")


class XMLFile(object):

    """ XML file object
    """

    def __init__(self, fname):
        """ constructor

        :param fname: XML file name
        :type fname: :obj:`str`
        """
        #: (:obj:`str`) XML file name
        self.fname = fname
        #: (:class:`lxml.etree.Element`) XML root instance
        self.elem = lxml.etree.Element("definition")

    def prettyPrint(self, etNode=None):
        """prints pretty XML making use of etree

        :param etNode: node
        :type etNode: :class:`lxml.etree.Element`
        """
        node = etNode if etNode is not None else self.elem
        if sys.version_info > (3,):
            xmls = _tostr(
                lxml.etree.tostring(
                    node, encoding='unicode',
                    method='xml', pretty_print=True))
        else:
            xmls = _tostr(
                lxml.etree.tostring(
                    node, encoding='utf-8',
                    method='xml', pretty_print=True))
        if not xmls.startswith("<?xml"):
            xmls = "<?xml version='1.0' encoding='utf-8'?>\n" + xmls
        return xmls

    def setDependencies(self, components, entry=None):
        """ sets tag content

        :param components: component dependencies
        :type components: :obj:`list` <:obj:`str`>
        :param entry: entry node
        :type entry: :class:`lxml.etree.Element`
        """
        text = "\n"
        for cp in components:
            text += "$components.%s\n" % cp
        if entry is not None:
            if entry.elem.tail is not None:
                entry.elem.tail += text
            else:
                entry.elem.tail = text
        else:
            if self.elem.text:
                self.elem.text += text
            else:
                self.elem.text = text

    def dump(self):
        """ dumps XML structure into the XML file

        :brief: It opens XML file, calls prettyPrint and closes the XML file
        """
        with open(self.fname, "w") as myfile:
            myfile.write(self.prettyPrint(self.elem))


def main():
    """ the main function
    """
    #: handler to XML file
    df = XMLFile("test.xml")
    #: entry
    en = NGroup(df, "entry1", "NXentry")
    #: instrument
    ins = NGroup(en, "instrument", "NXinstrument")
    #:    NXsource
    src = NGroup(ins, "source", "NXsource")
    #: field
    f = NField(src, "distance", "NX_FLOAT")
    f.setUnits("m")
    f.setText("100.")

    df.dump()


if __name__ == "__main__":
    main()
