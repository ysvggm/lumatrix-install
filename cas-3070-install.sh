#!/bin/bash

echo "Install target is: " $1
scp ifcfg-enp5s0 root@$1:/etc/sysconfig/network-scripts/
scp ifcfg-br-ex root@$1:/etc/sysconfig/network-scripts/
scp newcrushmap root@$1:/root/
ssh $1 ceph osd setcrushmap -i /root/newcrushmap
ssh $1 ceph osd pool rm rbd rbd --yes-i-really-really-mean-it
ssh $1 ceph osd pool create rbd 16
ssh $1 ceph osd pool create volumes 16
ssh $1 ceph osd pool create images 16
ssh $1 ceph osd pool create backups 16
ssh $1 ceph osd pool create vms 16
