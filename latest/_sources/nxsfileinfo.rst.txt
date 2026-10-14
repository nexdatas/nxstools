===========
nxsfileinfo
===========

Description
-----------

The nxsfileinfo program show metadata from nexus files

Synopsis
--------

.. code:: bash

	  nxsfileinfo <command> [options] <nexus_file_name>


The following commands are available: general, field, metadata, origdatablock, sample, instrument, attachment


nxsfileinfo general
-------------------

It shows general information for he nexus file.

Synopsis
""""""""

.. code:: bash

	  nxsfileinfo general <nexus_file_name>

Options:
  -h, --help            show this help message and exit
  --h5py                use h5py module as a nexus reader
  --h5cpp               use h5cpp module as a nexus reader

Example
"""""""

.. code:: bash

	  nxsfileinfo general saxs_ref1_02.nxs

nxsfileinfo field
-----------------

It shows field information for the nexus file.

Synopsis
""""""""

.. code:: bash

	  Usage: nxsfileinfo field [options]  <file_name>

Options:
   -h, --help            show this help message and exit
   -c HEADERS, --columns=HEADERS
       names of column to be shown (separated by commas without spaces). The possible names are: depends_on, dtype, full_path, nexus_path, nexus_type, shape, source, source_name, source_type, strategy, trans_type, trans_offset, trans_vector, units, value
   -f FILTERS, --filters=FILTERS
       full_path filters (separated by commas without spaces). Default: '*'. E.g. '*:NXsample/*'
   -v VALUES, --values=VALUES
       field names which value should be stored (separated by commas without spaces). Default: depends_on
   -g, --geometry        show fields with geometry full_path filters, i.e. *:NXtransformations/*,*/depends_on. It works only when -f is not defined
   -s, --source          show datasource parameters
   --h5py                use h5py module as a nexus reader
   --h5cpp               use h5cpp module as a nexus reader


Example
"""""""

.. code:: bash

	  nxsfileinfo field /tmp/saxs_ref1_02.nxs
          nxsfileinfo field /user/data/myfile.nxs -g
          nxsfileinfo field /user/data/myfile.nxs -s

nxsfileinfo metadata
--------------------

It shows metadata of the nexus file.

Synopsis
""""""""

.. code:: bash

	  Usage: nxsfileinfo metadata [options] <file_name>

Options:
   -h, --help            show this help message and exit
   -a ATTRS, --attributes ATTRS
                        names of field or group attributes to be show (separated by commas without spaces). The default takes all attributes
   -n NATTRS, --hidden-attributes NATTRS
                        names of field or group attributes to be hidden (separated by commas without spaces). The default: 'nexdatas_source,nexdatas_strategy'
   -v VALUES, --values VALUES
                        field names of more dimensional datasets which value should be shown (separated by commas without spaces)
   -z KEYWORDS, --keywords KEYWORDS
                        dataset keywords separated by commas.
   -w OWNERGROUP, --owner-group OWNERGROUP
                        owner group name. Default is {beamtimeid}-part
   -c ACCESSGROUPS, --access-groups ACCESSGROUPS
                        access group names separated by commas. Default is
                        {beamtimeid}-clbt,{beamtimeId}-dmgt,{beamline}dmgt

   -g GROUP_POSTFIX, --group-postfix GROUP_POSTFIX
                        postfix to be added to NeXus group name. The default: 'Parameters'
   -t ENTRYCLASSES, --entry-classes ENTRYCLASSES
                        names of entry NX_class to be shown (separated by commas without spaces). If name is '' all groups are shown. The default: 'NXentry'
   -e ENTRYNAMES, --entry-names ENTRYNAMES
                        names of entry groups to be shown (separated by commas without spaces). If name is '' all groups are shown. The default: ''
   -m, --raw-metadata    do not store NXentry as scientificMetadata
   --dont-merge          keep entries separate
   --add-empty-units     add empty units for fields without units
   --oned                add 1d values to scientificMetadata
   --max-oned-size MAXONEDSIZE
                         add min and max (or first and last) values of 1d records to scientificMetadata if its size excides --max-oned-size value
   -p PID, --pid PID
                        dataset pid
   -i BEAMTIMEID, --beamtimeid BEAMTIMEID
                        beamtime id
   -u, --pid-with-uuid
                        generate pid with uuid
   -f, --pid-with-filename
                        generate pid with file name
   -q TECHNIQUES, --techniques TECHNIQUES
                        names of techniques (separated by commas without
                        spaces).The default: ''
   -j SAMPLEID, --sample-id SAMPLEID
                        sampleId
   --sample-id-from-name  get sampleId from the sample name
   -y INSTRUMENTID, --instrument-id INSTRUMENTID
                        instrumentId
   --raw-instrument-id   leave raw instrument id
   -b BEAMTIMEMETA, --beamtime-meta BEAMTIMEMETA
                        beamtime metadata file
   -s SCIENTIFICMETA, --scientific-meta SCIENTIFICMETA
                        scientific metadata file
   -o OUTPUT, --output OUTPUT
                        output scicat metadata file
   -r RELPATH, --relative-path RELPATH
                        relative path to the scan files
   -x CHMOD, --chmod CHMOD
                        json metadata file mod bits, e.g. 0o662
   --copy-map COPYMAP   json or yaml map {output: input} or [[output, input],]
                        or a text file list to re-arrange metadata
   --copy-map-field COPYMAPFIELD
                        field json or yaml with map {output: input} or [[output, input],]
			or a text file list to re-arrange metadata. The default:
			'scientificMetadata.nxsfileinfo_parameters.copymap.value'
   --copy-map-error      Raise an error when the copy map file does not exist
   --copy-map-file COPYMAPFILE
                        json or yaml file containing the copy map, see also --copy-map
   -f FILEFORMAT, --file-format FILEFORMAT
                        input file format, e.g. 'nxs'. Default is defined by the file extension

   --proposal-as-proposal
                        Store the DESY proposal as the SciCat proposal
   --h5py               use h5py module as a nexus reader
   --h5cpp              use h5cpp module as a nexus reader

Example
"""""""

.. code:: bash

          nxsfileinfo metadata /user/data/myfile.nxs
          nxsfileinfo metadata /user/data/myfile.fio
          nxsfileinfo metadata /user/data/myfile.nxs -p 'Group'
          nxsfileinfo metadata /user/data/myfile.nxs -s
          nxsfileinfo metadata /user/data/myfile.nxs -a units,NX_class

nxsfileinfo origdatablock
-------------------------

It generates description of all scan files

Synopsis
""""""""

.. code:: bash

	  Usage: nxsfileinfo origdatablock [options] <scan_name>

Options:
  -h, --help            show this help message and exit
  -p PID, --pid PID     dataset pid
  -o OUTPUT, --output OUTPUT
                        output scicat metadata file
  -w OWNERGROUP, --owner-group OWNERGROUP
                        owner group name. Default is {beamtimeid}-part
  -c ACCESSGROUPS, --access-groups ACCESSGROUPS
                        access group names separated by commas. Default is
                        {beamtimeid}-clbt,{beamtimeId}-dmgt
  -s SKIP, --skip SKIP  filters for files to be skipped (separated by commas
                        without spaces). Default: ''. E.g.
			'*.pyc,*\~'
  -a ADD, --add ADD     list of files to be added (separated by commas
                        without spaces). Default: ''. E.g.
                        'scan1.nxs,scan2.nxs'
  -r RELPATH, --relative-path RELPATH
                        relative path to the scan files
  -x CHMOD, --chmod CHMOD
                        json metadata file mod bits, e.g. 0o662

Example
"""""""

.. code:: bash

	  nxsfileinfo origdatablock /user/data/scan_12345

nxsfileinfo sample
------------------

It generates description of sample

Synopsis
""""""""

.. code:: bash

	  Usage: nxsfileinfo sample [options]

Options:
  -h, --help            show this help message and exit
  -s SAMPLEID, --sample-id SAMPLEID
                        sample id
  -i BEAMTIMEID, --beamtimeid BEAMTIMEID
                        beamtime id
  -b BEAMLINE, --beamline BEAMLINE
                        beamline
  -d DESCRIPTION, --description DESCRIPTION
                        sample description
  -r OWNER, --owner OWNER
                        sample owner
  -p, --published       sample is published
  -w OWNERGROUP, --owner-group OWNERGROUP
                        owner group name. Default is {beamtimeid}-dmgt
  -c ACCESSGROUPS, --access-groups ACCESSGROUPS
                        access group names separated by commas. Default is {be
                        amtimeId}-dmgt,{beamtimeid}-clbt,{beamtimeId}-part,{be
                        amline}dmgt,{beamline}staff
  -x CHMOD, --chmod CHMOD
                        json metadata file mod bits, e.g. 0o662
  -m CHARACTERISTICSMETA, --sample-characteristics CHARACTERISTICSMETA
                        sample characteristics metadata file
  -o OUTPUT, --output OUTPUT
                        output scicat metadata file

Example
"""""""

.. code:: bash

          nxsfileinfo sample -i petra3/h2o/234234 -d 'HH water' -s ~/cm.json

nxsfileinfo instrument
----------------------

It generates description of instrument

Synopsis
""""""""

.. code:: bash

	  Usage: nxsfileinfo instrument [options]

Options:
  -h, --help            show this help message and exit
  -p PID, --pid PID     instrument pid
  -n NAME, --name NAME  instrument name
  -i BEAMTIMEID, --beamtimeid BEAMTIMEID
                        beamtime id
  -b BEAMLINE, --beamline BEAMLINE
                        beamline
  -w OWNERGROUP, --owner-group OWNERGROUP
                        owner group name. Default is {beamtimeid}-dmgt
  -c ACCESSGROUPS, --access-groups ACCESSGROUPS
                        access group names separated by commas. Default is {be
                        amtimeId}-dmgt,{beamtimeid}-clbt,{beamtimeId}-part,{be
                        amline}dmgt,{beamline}staff
  -x CHMOD, --chmod CHMOD
                        json metadata file mod bits, e.g. 0o662
  -m CUSTOMMETA, --custom-metadata CUSTOMMETA
                        instrument characteristics metadata file
  -o OUTPUT, --output OUTPUT
                        output scicat metadata file

Example
"""""""

.. code:: bash

	  nxsfileinfo instrument -p /petra3/p00 -n P00 -m ~/cm.json

nxsfileinfo attachment
----------------------

It generates description of attachment

Synopsis
""""""""

.. code:: bash

	  Usage: nxsfileinfo attachment [options] <image_file|scan_file>

Options:
  -h, --help            show this help message and exit
  -a ATID, --id ATID    attachment id
  -t CAPTION, --caption CAPTION
                        caption text
  -i BEAMTIMEID, --beamtimeid BEAMTIMEID
                        beamtime id
  -b BEAMLINE, --beamline BEAMLINE
                        beamline
  -r OWNER, --owner OWNER
                        attachment owner
  -w OWNERGROUP, --owner-group OWNERGROUP
                        owner group name. Default is {beamtimeid}-dmgt
  -c ACCESSGROUPS, --access-groups ACCESSGROUPS
                        access group names separated by commas. Default is {be
                        amtimeId}-dmgt,{beamtimeid}-clbt,{beamtimeId}-part,{be
                        amline}dmgt,{beamline}staff
  -f FILEFORMAT, --file-format FILEFORMAT
                        input file format, e.g. 'nxs'. Default is defined by
                        the file extension
  --h5py                use h5py module as a nexus reader
  --h5cpp               use h5cpp module as a nexus reader
  -x CHMOD, --chmod CHMOD
                        json metadata file mod bits, e.g. 0o662
  -s SIGNALS, --signals SIGNALS
                        signals data name(s) separated by comma
  -e AXES, --axes AXES  axis/axes data name(s) separated by comma
  -q SCANCMDAXES, --scan-command-axes SCANCMDAXES
                        a JSON dictionary with scan-command axes to override,
                        axis/axes data name(s) separated by comma for
                        detectors and by semicolon for more plots. Default:
                        {"hklscan":"h;k;l","qscan":"qz;qpar"}
  -m FRAME, --frame FRAME
                        a frame number for if more 2D images in the data
  --signal-label SLABEL
                        signal label
  --xlabel XLABEL       x-axis label
  --ylabel YLABEL       y-axis label
  -u, --override        override NeXus entries by script parameters
  --parameters-in-caption
                        add plot paramters to the caption
  -n NEXUSPATH, --nexus-path NEXUSPATH
                        base nexus path to element to be shown.
			If th path is '' the default group is shown. The default: ''

  -o OUTPUT, --output OUTPUT
                        output scicat metadata file


Example
"""""""

.. code:: bash

	  nxsfileinfo attachment -b p00 -i 2342342 -t 'HH water' -o ~/at1.json thumbnail.png
	  nxsfileinfo attachment -b p00 -i 2342342 -t 'HH water' -o ~/at2.json -s pilatus myscan_00123.nxs
	  nxsfileinfo attachment -b p00 -i 2342342 -t 'HH water' -o ~/at2.json  myscan_00124.fio


nxsfileinfo groupmetadata
-------------------------

It groups scan metadata to one dataset

Synopsis
""""""""

.. code:: bash

	  Usage: nxsfileinfo groupmetadata [options] [groupname]

Options:
  -h, --help            show this help message and exit
  -p PID, --pid PID     dataset pid
  --raw                 raw dataset type
  -i BEAMTIMEID, --beamtimeid  BEAMTIMEID beamtime id
  -s, --skip-group-datablock
                        skip group datablock
  -w, --allow-duplication
                        allow to merge metadata with duplicated pid
  -q, --raw             raw dataset type
  -f, --write-files     write output to files
  -k SCICATVERSION, --scicat-version SCICATVERSION
                        major scicat version metadata
  -x CHMOD, --chmod CHMOD
                        json metadata file mod bits, e.g. 0o662
  -g GROUPMAP, --group-map GROUPMAP
                        json or yaml map of {output: input} or [[output,
                        input],] or a text file list to re-arrange metadata
  -e, --group-map-error
                        Raise an error when the group map file does not exist
  -r GROUPMAPFILE, --group-map-file GROUPMAPFILE
                        json or yaml file containing the copy map, see also
  -m METADATAFILE, --metadata METADATAFILE
                        json metadata file
  -d ORIGDATABLOCKFILE, --origdatablock ORIGDATABLOCKFILE
                        json origmetadata file
  -a ATTACHMENTFILE, --attachment ATTACHMENTFILE
                        json attachment file
  -o OUTPUT, --output OUTPUT
                        output scicat group metadata file
  -l DBOUTPUT, --datablock-output DBOUTPUT
                        output scicat group datablocks list file
  -t ATOUTPUT, --attachment-output ATOUTPUT
                        output scicat group attachments list file

Example
"""""""

.. code:: bash

	  nxsfileinfo groupmetadata -o /user/data/myscan.scan.json  -t /user/data/myscan.attachment.json  -l /user/data/myscan.origdatablock.json  -c /home/user/group_config.txt  -m /user/data/myscan_00023.scan.json  -d /user/data/myscan_00023.origdatablock.json  -a /user/data/myscan_00023.attachment.json

	  nxsfileinfo groupmetadata myscan_m001  -m /user/data/myscan_00021.scan.json -c /home/user/group_config.txt

	  nxsfileinfo groupmetadata  myscan_m001  -c /home/user/group_config.txt  -m /user/data/myscan_00023.scan.json  -d /user/data/myscan_00023.origdatablock.json  -a /user/data/myscan_00023.attachment.json

	  nxsfileinfo groupmetadata  -m /user/data/myscan_00023.scan.json  -d /user/data/myscan_00023.origdatablock.json  -c /home/user/group_config.txt
