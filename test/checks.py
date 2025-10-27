#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2017 DESY, Jan Kotanski <jkotan@mail.desy.de>
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
# \package test nexdatas.configserver
# \file checks.py
# checks
#
import sys
import xml.etree.ElementTree as et
from lxml.etree import XMLParser
from functools import cmp_to_key


def cmpnodes(n1, n2):
    """ compare etree nodes

    :param n1: first node
    :type n1: :obj:`xml.etree.ElementTree.Element`
    :param n2: second node
    :type n2: :obj:`xml.etree.ElementTree.Element`
    """
    if n1.tag > n2.tag:
        return 1
    elif n1.tag < n2.tag:
        return -1
    elif (n1.tail or "") > (n2.tail or ""):
        return 1
    elif (n1.tail or "") < (n2.tail or ""):
        return -1

    n1at = n1.attrib.items()
    n2at = n2.attrib.items()
    n1at.sort()
    n2at.sort()
    if n1at < n2at:
        return -1
    elif n1at > n2at:
        return 1

    ln1 = list(n1)
    ln2 = list(n2)
    if sys.version_info > (3,):
        ln1.sort(key=cmp_to_key(cmpnodes))
        ln2.sort(key=cmp_to_key(cmpnodes))
    else:
        ln1.sort(cmp=cmpnodes)
        ln2.sort(cmp=cmpnodes)

    for c1, c2 in zip(ln1, ln2):
        val = cmpnodes(c1, c2)
        if val < 0:
            return -1
        elif val > 0:
            return 1
    return 0


def checknodes(utest, n1, n2):
    """ compare etree nodes via unittests

    :param utest: unittest case object
    :type utest: :obj:`unittest.TestCase`
    :param n1: first node
    :type n1: :obj:`xml.etree.ElementTree.Element`
    :param n2: second node
    :type n2: :obj:`xml.etree.ElementTree.Element`
    """
    utest.assertEqual(n1.tag, n2.tag)
    utest.assertEqual(n1.text, n2.text)
    if n1.tail and n2.tail:
        utest.assertEqual(n1.tail.strip(), n2.tail.strip())
    else:
        utest.assertEqual(n1.tail, n2.tail)
    utest.assertEqual(len(n1.attrib), len(n2.attrib))
    for k, v in n1.attrib.items():
        utest.assertTrue(k in n2.attrib.keys())
        utest.assertEqual(v, n2.attrib[k])
    utest.assertEqual(len(n1), len(n2))
    ln1 = list(n1)
    ln2 = list(n2)
    if sys.version_info > (3,):
        ln1.sort(key=cmp_to_key(cmpnodes))
        ln2.sort(key=cmp_to_key(cmpnodes))
    else:
        ln1.sort(cmp=cmpnodes)
        ln2.sort(cmp=cmpnodes)
    for c1, c2 in zip(ln1, ln2):
        checknodes(utest, c1, c2)


def checkxmls(utest, xml1, xml2):
    """ compare xmls via unittests

    :param utest: unittest case object
    :type utest: :obj:`unittest.TestCase`
    :param xml1: first xml
    :type xml1: :obj:`str`
    :param xml2: second xml to compare
    :type xml2: :obj:`str`
    """
    n1 = et.fromstring(
        xml1,
        parser=XMLParser(collect_ids=False,
                         remove_blank_text=True))
    n2 = et.fromstring(
        xml2,
        parser=XMLParser(collect_ids=False,
                         remove_blank_text=True))
    try:
        checknodes(utest, n1, n2)
    except Exception:
        print("%s\n!=\n%s" % (xml1, xml2))
        raise


def checknxmls(utest, xml1, xmls):
    """ compare xmls via unittests

    :param utest: unittest case object
    :type utest: :obj:`unittest.TestCase`
    :param xml1: first xml
    :type xml1: :obj:`str`
    :param xmls: list of xml to compare
    :type xmls: :obj:`list` < :obj:`str` >
    """

    n1 = et.fromstring(
        xml1,
        parser=XMLParser(collect_ids=False,
                         remove_blank_text=True))
    ns = []
    for xml2 in xmls:
        ns.append(
            et.fromstring(
                xml2,
                parser=XMLParser(collect_ids=False,
                                 remove_blank_text=True)))
    for i, n2 in enumerate(ns):
        try:
            checknodes(utest, n1, n2)
            break
        except Exception:
            print("%s\n!=\n%s" % (xml1, xml2))
            if i + 1 == len(ns):
                raise
