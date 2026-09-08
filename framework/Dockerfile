FROM ubuntu:focal AS base

# Install dependencies
RUN apt update

RUN DEBIAN_FRONTEND=noninteractive apt install -y \
     build-essential \
     cmake \
     libfftw3-dev \
     libmbedtls-dev \
     libboost-program-options-dev \
     libconfig++-dev \
     libsctp-dev \
     libzmq3-dev \
     curl \
     iputils-ping \
     iproute2 \
     iptables \
     unzip \
     git
     
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /srsran

# Pinned git commit used for this example
ARG COMMIT=48cfe041f06942bb32213a126f7706a46a676713

RUN git clone https://github.com/srsRAN/srsRAN.git ./
RUN git fetch origin ${COMMIT}
RUN git checkout ${COMMIT}

WORKDIR /srsran/build

RUN cmake ../
RUN make -j2
RUN make install
RUN srsran_install_configs.sh service

RUN ldconfig

WORKDIR /srsran