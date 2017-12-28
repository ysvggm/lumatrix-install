#!/bin/bash

echo "Install fio"
yum install -y libaio-devel gcc wget
wget http://brick.kernel.dk/snaps/fio-2.1.tar.gz
tar zxvf fio-2.1.tar.gz 
cd fio-2.1
configure
make
make install

echo "Partition and format test disk"
fdisk /dev/vdb <<EOF
n
p
1


w
EOF
mkfs.ext4 /dev/vdb1
echo "Now test"
echo "Test sequential write"
/usr/local/bin/fio -filename=/dev/vdb1 -direct=1 -iodepth 1 -thread -rw=write -ioengine=psync -bs=16k -size=200G -numjobs=30 -runtime=1000 -name=jicki
echo "Test random write"
/usr/local/bin/fio -filename=/dev/vdb1 -direct=1 -iodepth 1 -thread -rw=randwrite -ioengine=psync -bs=16k -size=200G -numjobs=30 -runtime=1000 -name=jicki
echo "Test sequential read"
/usr/local/bin/fio -filename=/dev/vdb1 -direct=1 -iodepth 1 -thread -rw=read -ioengine=psync -bs=16k -size=200G -numjobs=30 -runtime=1000 -name=jicki
echo "Test random read"
/usr/local/bin/fio -filename=/dev/vdb1 -direct=1 -iodepth 1 -thread -rw=randread -ioengine=psync -bs=16k -size=200G -numjobs=30 -runtime=1000 -name=jicki
