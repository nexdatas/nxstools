FROM debian:bookworm

# MAINTAINER DESY, Jan Kotanski <jankotan@gmail.com>
RUN /bin/bash -c 'echo "deb http://ftp.de.debian.org/debian bookworm main" > /etc/apt/sources.list.d/debiande.list'
RUN apt-get -qq update && apt-get -qq install -y libterm-readline-gnu-perl software-properties-common coreutils gnupg2 procps apt-utils curl apt-transport-https gnupg2 ca-certificates wget

RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
RUN curl -s http://repos.pni-hdri.de/debian_repo.pub.gpg  | gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/debian-hdri-repo.gpg --import
RUN chmod 644 /etc/apt/trusted.gpg.d/debian-hdri-repo.gpg
# RUN add-apt-repository "deb http://repos.pni-hdri.de/apt/debian bookworm main" -y
RUN cd /etc/apt/sources.list.d && wget http://repos.pni-hdri.de/bookworm-pni-hdri.list


RUN apt-get -qq update && apt-get -qq -y dist-upgrade
RUN apt-get -qq update && apt-get -qq install -y default-mysql-client  python3-h5py  python3-mysqldb python3-sphinx  apt-utils debconf-utils net-tools  omniidl libomniorb4-dev libcos4-dev libomnithread4-dev libzmq3-dev python3-pninexus python3-argcomplete python3-tz python3-lxml python3-pytest bitshuffle-serial-links hdf5-filter-plugin-serial-links   liblog4j1.2-java python3-whichcraft python3-fabio python3-setuptools python3-yaml python3-pytest-cov python3-pil python3-matplotlib xvfb  libxcb1 libx11-xcb1 libxcb-keysyms1 libxcb-image0 libxcb-icccm4 libxcb-render-util0 xkb-data
# hdf5-plugin-bz2 hdf5-plugin-lz4

RUN useradd -ms /bin/bash tango
RUN  /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "mysql-server mysql-server/root_password password rootpw"; debconf-set-selections <<< "mysql-server mysql-server/root_password_again password rootpw"; debconf-set-selections <<< "mariadb-server mysql-server/root_password password rootpw"; debconf-set-selections <<< "mariadb-server mysql-server/root_password_again password rootpw"; debconf-get-selections |grep mysql '
RUN apt-get -qq install -y default-mysql-server adduser python3-mysqldb
RUN  /bin/bash -c 'sleep 10'
RUN /bin/bash -c 'export DEBIAN_FRONTEND=noninteractive; debconf-set-selections <<< "tango-db tango-db/db/app-user string tango"; debconf-set-selections <<< "tango-db tango-db/mysql/app-pass	password rootpw"; debconf-set-selections <<< "tango-db tango-db/mysql/admin-pass password rootpw"; debconf-set-selections <<< "tango-db tango-db/password-confirm password rootpw"; debconf-set-selections <<< "tango-db tango-db/app-password-confirm password rootpw"; debconf-set-selections <<< "nxsconfigserver-db nxsconfigserver-db/mysql/app-pass password rootpw"; debconf-set-selections <<< "nxsconfigserver-db nxsconfigserver-db/mysql/admin-pass password rootpw"; debconf-set-selections <<< "nxsconfigserver-db nxsconfigserver-db/app-password-confirm password rootpw"; debconf-set-selections <<< "nxsconfigserver-db nxsconfigserver-db/db/app-user string tango"'

RUN  sed -i "s/\[mysql\]/\[mysqld\]\nsql_mode = NO_ZERO_IN_DATE,NO_ENGINE_SUBSTITUTION\ncharacter_set_server=latin1\ncollation_server=latin1_swedish_ci\n\[mysql\]/g" /etc/mysql/conf.d/mysql.cnf

ENV PKG_CONFIG_PATH=/home/tango/lib/pkgconfig
# ENV HDF5_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/hdf5/plugins
ENV HDF5_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/hdf5/serial/plugins
USER tango
WORKDIR /home/tango
