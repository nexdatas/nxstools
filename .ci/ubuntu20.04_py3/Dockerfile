FROM ubuntu:20.04

MAINTAINER DESY, Jan Kotanski <jankotan@gmail.com>

ENV DEBIAN_FRONTEND=noninteractive
RUN sed -i 's|http://archive|http://de.archive|g' /etc/apt/sources.list
RUN apt-get -qq update && apt-get -qq install -y libterm-readline-gnu-perl software-properties-common coreutils gnupg2 procps apt-utils curl apt-transport-https gnupg2 ca-certificates wget
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
RUN curl --retry 10 -s http://repos.pni-hdri.de/debian_repo.pub.gpg  | gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/debian-hdri-repo.gpg --import
RUN chmod 644 /etc/apt/trusted.gpg.d/debian-hdri-repo.gpg
RUN add-apt-repository "deb http://repos.pni-hdri.de/apt/debian focal main" -y
RUN apt-get -qq update && export DEBIAN_FRONTEND=noninteractive && apt-get -qq dist-upgrade
RUN apt-get -qq update && export DEBIAN_FRONTEND=noninteractive && apt-get  install -y -qq mysql-client mysql-client python3-h5py python3-sphinx apt-utils debconf-utils net-tools  omniidl libomniorb4-dev libcos4-dev libzmq3-dev python3-distutils python3-pninexus python3-argcomplete python3-tz python3-lxml python3-pytest  hdf5-plugin-bshuf hdf5-plugin-bz2 hdf5-plugin-lz4  python3-whichcraft python3-fabio python3-setuptools liblog4j1.2-java python3-yaml python3-pytest-cov python3-pil python3-matplotlib xvfb  libxcb1 libx11-xcb1 libxcb-keysyms1 libxcb-image0 libxcb-icccm4 libxcb-render-util0 xkb-data

# install h5py 2.10
RUN export DEBIAN_FRONTEND=noninteractive && apt-get -qq install -y git libhdf5-dev python3-dev cython3 python3-numpy
RUN /bin/bash -c 'git clone -b 2.10.x https://github.com/h5py/h5py h5py;cd h5py; python3 setup.py install'

RUN useradd -ms /bin/bash tango
RUN  /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "mysql-server mysql-server/root_password password rootpw"'
RUN  /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "mysql-server mysql-server/root_password_again password rootpw"'
RUN apt-get -qq update && apt-get -qq install -y python3-mysqldb mysql-server
RUN  /bin/bash -c 'sleep 10'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "tango-db tango-db/db/app-user string tango"'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "tango-db tango-db/mysql/app-pass	password rootpw"'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "tango-db tango-db/mysql/admin-pass password rootpw"'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "tango-db tango-db/password-confirm password rootpw"'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "tango-db tango-db/app-password-confirm password rootpw"'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "nxsconfigserver-db nxsconfigserver-db/mysql/app-pass password rootpw"'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "nxsconfigserver-db nxsconfigserver-db/mysql/admin-pass password rootpw"'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "nxsconfigserver-db nxsconfigserver-db/app-password-confirm password rootpw"'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "nxsconfigserver-db nxsconfigserver-db/db/app-user string tango"'


RUN  sed -i "s/\[mysql\]/\[mysqld\]\nsql_mode = NO_ZERO_IN_DATE,NO_ENGINE_SUBSTITUTION\ncharacter_set_server=latin1\ncollation_server=latin1_swedish_ci\n\[mysql\]/g" /etc/mysql/mysql.conf.d/mysql.cnf

ENV PKG_CONFIG_PATH=/home/tango/lib/pkgconfig
# ENV HDF5_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/hdf5/plugins
ENV MYSQL_HOST=127.0.0.1
USER tango
WORKDIR /home/tango

