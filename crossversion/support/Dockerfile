# ------------------------------------------------------------
# OS: CentosStream 8
# https://quay.io/repository/centos/centos
# ------------------------------------------------------------
FROM quay.io/centos/centos:stream8


# ------------------------------------------------------------
# Metadata
# ------------------------------------------------------------
LABEL maintainer="jjhursey@open-mpi.org"

ARG LIBEVENT_INSTALL_PATH=/home/pmixer/local/libevent
ARG HWLOC1_INSTALL_PATH=/home/pmixer/local/hwloc-1x
ARG HWLOC_INSTALL_PATH=/home/pmixer/local/hwloc

LABEL com.ibm.hwloc.version=2.4.0
LABEL com.ibm.hwloc1.version=1.11.13
LABEL com.ibm.libevent.version=2.4.0


# ------------------------------------------------------------
# Install required packages
# Remove: pandoc
# python2: The xversion script is Python 2 at the moment and
#          needs the default python to point to that.
# ------------------------------------------------------------
RUN yum -y update && \
    yum -y install epel-release && \
    yum -y install \
        gcc gcc-gfortran gcc-c++ gdb \
        binutils less wget which sudo make file \
        wget git autoconf automake libtool flex \
        perl-Data-Dumper bzip2 man diffutils \
        python2 python3 \
        python3-devel \
        zlib-devel \
 && yum clean all \
 && alternatives --set python /usr/bin/python2


# -----------------------------
# Add a user, so we don't run as root
# -----------------------------
RUN groupadd -r pmixer && useradd --no-log-init -r -m -b /home -g pmixer pmixer
USER pmixer
WORKDIR /home/pmixer

ENV AUTOMAKE_JOBS=20


# -----------------------------
# Cython
# -----------------------------
RUN pip3 install --user Cython
ENV PYTHONPATH=/home/pmixer/.local/lib/python3.6/site-packages


# -----------------------------
# Install libevent and hwloc (both 2.x and 1.x)
# -----------------------------
RUN mkdir -p /home/pmixer/local
ADD --chown=pmixer:pmixer src /home/pmixer/local/src

ENV LIBEVENT_INSTALL_PATH=$LIBEVENT_INSTALL_PATH
ENV HWLOC1_INSTALL_PATH=$HWLOC1_INSTALL_PATH
ENV HWLOC_INSTALL_PATH=$HWLOC_INSTALL_PATH

RUN cd /home/pmixer/local/src && \
    tar -zxf libevent* && \
    cd libevent-2.1.8-stable && \
    ./configure --prefix=${LIBEVENT_INSTALL_PATH} > /dev/null && \
    make > /dev/null && \
    make install > /dev/null && \
    cd /home/pmixer/local/src && \
    tar -zxf hwloc-1* && \
    cd hwloc-1.11.13 && \
    ./configure --prefix=${HWLOC1_INSTALL_PATH} > /dev/null && \
    make > /dev/null && \
    make install > /dev/null && \
    cd /home/pmixer/local/src && \
    tar -zxf hwloc-2* && \
    cd hwloc-2.4.0 && \
    ./configure --prefix=${HWLOC_INSTALL_PATH} > /dev/null && \
    make > /dev/null && \
    make install > /dev/null && \
    cd .. && \
    rm -rf /home/pmixer/local/src


# -----------------------------
# Force a rebuild from this point
# Otherwise Docker will not know that the following scripts do the checking
# for updates and skip them (using the cached versions).
# -----------------------------
ARG BUILD_TIMESTAMP=unknown
ENV BUILD_TIMESTAMP=$BUILD_TIMESTAMP
RUN echo "BUILD_TIMESTAMP: ["$BUILD_TIMESTAMP"]"


# -----------------------------
# Checkout the pmix-tests repo
# -----------------------------
RUN cd /home/pmixer && \
    git clone https://github.com/pmix/pmix-tests


# -----------------------------
# Build full set of versions
# -----------------------------
RUN mkdir -p /home/pmixer/scratch
RUN cd /home/pmixer/pmix-tests/crossversion && \
    ./xversion.py --basedir=$HOME/scratch \
         --with-hwloc=${HWLOC_INSTALL_PATH} \
         --with-hwloc1=${HWLOC1_INSTALL_PATH} \
         --with-libevent=${LIBEVENT_INSTALL_PATH} \
         -r -q


# -----------------------------
# Add scripts directory
# -----------------------------
ADD --chown=pmixer:pmixer bin /home/pmixer/bin

# -----------------------------
# Entrypoint
# -----------------------------
CMD ["/home/pmixer/bin/run-xversion.sh"]
