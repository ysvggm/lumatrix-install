#!/bin/bash

echo "Install target is: " $1
echo "Install openstack all-in-one"
yum install -y centos-release-openstack-ocata
yum update -y
yum install -y openstack-packstack
sed -i 's/$db_sync_timeout = 300/$db_sync_timeout = 1200/' /usr/share/openstack-puppet/modules/nova/manifests/db/sync.pp
sed -i 's/$db_sync_timeout = 300/$db_sync_timeout = 1200/' /usr/share/openstack-puppet/modules/neutron/manifests/db/sync.pp
packstack --answer-file=./packstack-answers.txt 
echo "Copy network scripts"
cp /etc/sysconfig/network-scripts/ifcfg-enp3s0f1 /etc/sysconfig/network-scripts/ifcfg-enp3s0f1.bkp
cp ifcfg-enp3s0f1 /etc/sysconfig/network-scripts/
cp ifcfg-br-ex /etc/sysconfig/network-scripts/
ifdown ifcfg-enp3s0f1
ifdown br-ex
ifup ifcfg-enp3s0f1
ifup br-ex
systemctl restart openvswitch.service
mv /etc/httpd/conf.d/15-default.conf /etc/httpd/conf.d/15-default.conf.bkp
sed -i 's/ServerAlias 127.0.0.1/## ServerAlias 127.0.0.1/' /etc/httpd/conf.d/15-horizon_vhost.conf
sed -i 's/ServerAlias ceph-node3/## ServerAlias ceph-node3/' /etc/httpd/conf.d/15-horizon_vhost.conf
sed -i 's/ServerAlias localhost/## ServerAlias localhost/' /etc/httpd/conf.d/15-horizon_vhost.conf
