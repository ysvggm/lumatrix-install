#!/bin/bash

echo "Install target is: " $1
echo "Set dns"
nmcli con mod enp1s0 ipv4.dns "8.8.8.8"
nmcli con up enp1s0
echo "Install openstack all-in-one"
yum install -y centos-release-openstack-ocata
yum update -y
yum install -y openstack-packstack
packstack --answer-file=./packstack-answers.txt --timeout=600
echo "Copy network scripts"
cp ifcfg-enp3s0f1 /etc/sysconfig/network-scripts/
cp ifcfg-br-ex /etc/sysconfig/network-scripts/
