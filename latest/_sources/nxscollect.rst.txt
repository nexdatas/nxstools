=========
nxcollect
=========

Description
-----------

The nxscollect is  a command-line tool dedicated to collect detector images.


The append sub-commnand adds images of external formats into the NeXus master file.
The images to collect should be denoted by postrun fields inside NXcollection groups or given by command-line parameters.

The link sub-commnand creates external or internal link in the NeXus master file to NeXus data files.


Synopsis for nxscollect append
------------------------------

.. code:: bash

          nxscollect append [-h] [-c COMPRESSION] [-p PATH] [-i INPUTFILES]
                         [--separator SEPARATOR] [--dtype DATATYPE]
                         [--shape SHAPE] [-s] [-r] [--test] [--h5py]
                         [--h5cpp]
                         [nexus_file [nexus_file ...]]


  nexus_file            nexus files to be collected

Options:
  -h, --help            show this help message and exit
  -c COMPRESSION, --compression COMPRESSION
                        deflate compression rate from 0 to 9 (default: 2) or
                        <filterid>:opt1,opt2,... e.g. -c 32008:0,2 for
                        bitshuffle with lz4
  -p PATH, --path PATH  nexus path for the output field, e.g.
                        /scan/instrument/pilatus/data
  -i INPUTFILES, --input_files INPUTFILES
                        input data files defined with a pattern or separated
                        by ',' e.g.'scan_%05d.tif:0:100'
  --separator SEPARATOR
                        input data files separator (default: ',')
  --dtype DATATYPE      datatype of input data - only for raw data, e.g.
                        'uint8'
  --shape SHAPE         shape of input data - only for raw data, e.g.
                        '[4096,2048]'
  -s, --skip_missing    skip missing files
  -r, --replace_nexus_file
                        if it is set the old file is not copied into a file
                        with .__nxscollect__old__* extension
  --test                execute in the test mode
  --h5py                use h5py module as a nexus reader/writer
  --h5cpp               use h5cpp module as a nexus reader/writer

Examples of nxscollect append
-----------------------------

.. code:: bash

       nxscollect append -c1 /tmp/gpfs/raw/scan_234.nxs

       nxscollect append -c32008:0,2 /ramdisk/scan_123.nxs

       nxscollect append --test /tmp/gpfs/raw/scan_234.nxs

       nxscollect append scan_234.nxs --path /scan/instrument/pilatus/data  --inputfiles 'scan_%05d.tif:0:100'


Synopsis for nxscollect link
----------------------------

.. code:: bash

          nxscollect link [-h] [-n NAME] [-t TARGET] [-r] [--test]
                       [--h5py] [--h5cpp]
                       [nexus_file_path]

  nexus_file_path       nexus files with the nexus directory to place the link

Options:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  link name
  -t TARGET, --target TARGET
                        link target with the file name if external
  -r, --replace_nexus_file
                        if it is set the old file is not copied into a file
                        with .__nxscollect__old__* extension
  --test                execute in the test mode
  --h5py                use h5py module as a nexus reader/writer
  --h5cpp               use h5cpp module as a nexus reader



Examples of nxscollect link
---------------------------

.. code:: bash

       nxscollect link scan_234.nxs://entry/instrument/lambda --name data --target lambda.nxs://entry/data/data

       nxscollect link scan_123.nxs://entry:NXentry/instrument/eiger:NXdetector  --target eiger.nxs://entry/data/data


Synopsis for nxscollect vds
---------------------------

.. code:: bash

          nxscollect vds [-h] [-e TARGETFIELDS] [--separator SEPARATOR]
                      [-t DTYPE] [-s SHAPE] [-f FILLVALUE] [-p SHAPES]
                      [-o OFFSETS] [-b BLOCKS] [-c COUNTS] [-d STRIDES]
                      [-l SLICES] [-P TARGETSHAPES] [-O TARGETOFFSETS]
                      [-B TARGETBLOCKS] [-C TARGETCOUNTS] [-D TARGETSTRIDES]
                      [-L TARGETSLICES] [-r] [--test] [--h5cpp] [--h5py]
                      [nexus_file_path_field]

create a virual dataset in the master file

nexus_file_path_field    nexus files with the nexus directory and a field name  to create the VDS field


Options:

  -h, --help            show this help message and exit
  -t DTYPE, --dtype DTYPE
                        datatype of the VDS field, e.g. 'uint8'
  -s SHAPE, --shape SHAPE
                        shape of the VDS field, e.g. '[U,4096,2048]' or
                        U,4096,2048 where U means span along the field'
  -f FILLVALUE, --fill-value FILLVALUE
                        fill value for the gaps, default is 0
  -e TARGETFIELDS, --target-fields TARGETFIELDS
                        external fields with their NeXus file paths defined
                        with a pattern or separated by ','
                        e.g.'scan_123/lambda_%05d.nxs://entry/data/data:0:3'
  --separator SEPARATOR
                        input data files separator (default: ',')
  -p SHAPES, --shapes SHAPES
                        shapes in the VDS layout hyperslab for the
                        corresponding target fields with coordinates sepatated
                        by ',' and different fields separated by ';', ':' or
                        spaces e.g.',,;,300,;,600,0' where an empty coordinate
                        means 0
  -o OFFSETS, --offsets OFFSETS
                        offsets in the VDS layout hyperslab for the
                        corresponding target fields with coordinates sepatated
                        by ',' and different fields separated by ';', ':' or
                        spaces e.g.',,;,300,;,600,0' where an empty coordinate
                        means 0
  -b BLOCKS, --blocks BLOCKS
                        block sizes in the VDS layout hyperslab for the
                        corresponding target fields with coordinates sepatated
                        by ',' and different fields separated by ';', ':' or
                        spaces e.g. ',256,512;,256,512;,256,512' where an
                        empty coordinate means 1
  -c COUNTS, --counts COUNTS
                        count numbers in the VDS layout hyperslabfor the
                        corresponding target fields with coordinates sepatated
                        by ',' and different fields separated by ';', ':' or
                        spaces e.g. ',1,1;,1,1;,1,1' where an empty coordinate
                        means span along the layout
  -d STRIDES, --strides STRIDES
                        stride sizes in the VDS layout hyperslabfor the
                        corresponding target fields with coordinates sepatated
                        by ',' and different fields separated by ';', ':' or
                        spaces e.g. ',,;,,;,,' where an empty coordinate means
                        1
  -l SLICES, --slices SLICES
                        mapping slices in the VDS layoutfor the corresponding
                        target fields with coordinates sepatated by ',' and
                        different fields separated by ';' or spaces e.g.
                        ':,0:50,: :,50:100,:' where U means span along the
                        layout
  -P TARGETSHAPES, --target-shapes TARGETSHAPES
                        field shapes with coordinates sepatated by ',' and
                        different fields separated by ';', ':' or spaces
                        e.g.',,;,300,;,600,0'
  -O TARGETOFFSETS, --target-offsets TARGETOFFSETS
                        offsets in the view hyperslab of target fieldswith
                        coordinates sepatated by ',' and different fields
                        separated by ';', ':' or spaces e.g.',,;,300,;,600,0'
                        where an empty coordinate means 0
  -B TARGETBLOCKS, --target-blocks TARGETBLOCKS
                        block sizes in the view hyperslab of target fields
                        with coordinates sepatated by ',' and different fields
                        separated by ';', ':' or spaces e.g.
                        ',256,512;,256,512;,256,512' where an empty coordinate
                        means 1
  -C TARGETCOUNTS, --target-counts TARGETCOUNTS
                        count numbers in the view hyperslab of target fields
                        with coordinates sepatated by ',' and different fields
                        separated by ';', ':' or spaces e.g. ',1,1;,1,1;,1,1'
                        where an empty coordinate means span along the layout
  -D TARGETSTRIDES, --target-strides TARGETSTRIDES
                        stride sizes numbers in the view hyperslab of target
                        fields with coordinates sepatated by ',' and different
                        fields separated by ';', ':' or spaces e.g. ',,;,,;,,'
                        where an empty coordinate means 1
  -L TARGETSLICES, --target-slices TARGETSLICES
                        view slices of target fields with coordinates
                        sepatated by ',' and different fields separated by ';'
                        or spaces e.g. ':,0:50,: :,0:50,:' where U means span
                        along the layout
  -r, --replace-nexus-file
                        if it is set the old file is not copied into a file
                        with .__nxscollect__old__* extension
  --test                execute in the test mode
  --h5cpp               use h5cpp module as a nexus reader
  --h5py                use h5py module as a nexus reader/writer



Examples of nxscollect vds
--------------------------

.. code:: bash

       nxscollect vds scan_234.nxs://entry/instrument/eiger/data  --shape '1000,2048,1024' --dtype uint32 --target-fields 'eiger_%05d.nxs://entry/data/data:1:10' --shapes '100,,:100,,:100,,:100,,:100,,:100,,:100,,:100,,:100,,:100,,'   --offsets '0,,:100,,:200,,:300,,:400,,:500,,:600,,:700,,:800,,:900,,'

           - creates VDS (shape [1000,2048,1024]) of ten nexus files (shape [100,2048,1024]) merged in their first dimension

       nxscollect vds scan_234.nxs://entry/instrument/lambda/data  --shape '100,300,762'  --dtype uint32 --target-fields 'lambda_%05d.nxs://entry/data/data:0:2' --shapes ',,250:,,250:,,250'   --offsets ',,:,,256:,,512'  --counts 'U,,:U,,:U,,' -f 1

           - creates VDS (shape [100,300,762]) of three nexus files (shape [100,300,250]) merged in their third dimension,
               separated with a 6 pixel gap of 1 values and unlimited first dimension

       nxscollect vds scan_234.nxs://entry/instrument/percival/data  --shape '4000,1600,2000' --dtype int16 --target-fields 'percival_%05d.nxs://entry/data/data:1:4' --shapes '1000,,:1000,,:1000,,:1000,,'   --offsets '0,,:1,,:2,,:3,,'  --counts 'U,,:U,,:U,,:U,,' --strides '4,,:4,,:4,,:4,,'

           - creates VDS (shape [1000,1600,2000]) of three nexus files (shape [1000,1600,2000])
                merged in their the first dimension with interlaying frames
                and unlimited first dimension
