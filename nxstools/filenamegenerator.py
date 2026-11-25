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

""" Filename generator """


class FilenameGenerator(object):

    """Generate image file names

    (c) Copyright 2015 Eugen Wintersberger <eugen.wintersberger@gmail.com>
    (c) Copyright 2015 DESY
    This file is part of nx2img.

    nx2img is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    nx2img is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with nx2img.  If not, see <http://www.gnu.org/licenses/>.

    Generator class creating image file names.

    :param fname_template: file name template
    :type fname_template: :obj:`str`
    :param start_index: file start index
    :type start_index: :obj:`int`
    :param stop_index: file stop index
    :type stop_index: :obj:`int`
    """

    def __init__(self, fname_template, start_index=0, stop_index=None):

        #: (:obj:`int`) file start index
        self.file_index = start_index
        #: (:obj:`str`) file name template
        self.file_template = fname_template
        #: (:obj:`int`) file stop index
        self.stop_index = stop_index

    def __call__(self):
        # if self.stop_index is -1 we loop forever, otherwise we stop
        # when the current index exceeds self.stop_index
        while self.stop_index is None or self.file_index <= self.stop_index:
            filename = self.file_template % (self.file_index)
            self.file_index += 1
            yield filename

    @staticmethod
    def from_slice(file_template):
        """
        Static factory method to create a filename_generator instance
        from a sliced user input

        :param file_template: file template
        :type file_template: :obj:`str`
        :returns: filename generator object
        :rtype: :class:`FilenameGenerator`
        """

        (file_format, start_index_str, stop_index_str) = \
            file_template.rsplit(":", 2)
        stop_index = None
        if stop_index_str is not None:
            stop_index = int(stop_index_str)

        start_index = int(start_index_str)

        return FilenameGenerator(file_format, start_index, stop_index)
