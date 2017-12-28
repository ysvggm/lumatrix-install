#!/usr/bin/python2
import subprocess
import json
import sys
from StringIO import StringIO
from socket import inet_aton,inet_ntoa
import struct
import re

import argparse
import os
import os_client_config
from openstack import connection
from openstack import profile
from openstack import utils
import sys

class cmdWrapper:

	loaded_json={}
	def __init__(self, cmd, **options):
		if options.get("noreturn") is not True:
			cmd += " -f json "
		p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE ,shell=True)
		out, err = p.communicate() 
		out_stringio = StringIO(out)
		out_string = out_stringio.read()
		err_stringio = StringIO(err)
		err_string = err_stringio.read()
		if len(err_string) > 0:
			err_string = "{\"error\":{\"msg\":\"" + re.sub(r'[\x00-\x1f\x7f-\x9f]', '', err_string) + "\"}}"
		out_json = {}
		err_json = {}
		if len(out_string) > 0:
			self.loaded_json = json.loads(out_string)
		if len(err_string) > 0:
			self.loaded_json = json.loads(err_string)
		return

class sdkWorker:
	def __init__(self, **options):
		conn = options.get("connection")
		if conn is None:
        		self.conn = self.create_connection()
		else:
			self.conn = conn

	def create_connection(self):
	    	prof = profile.Profile()
	    	prof.set_region(profile.Profile.ALL, "RegionOne")
	    	return connection.Connection(
	        	profile=prof,
	        	user_agent='examples',
	        	auth_url=os.environ['OS_AUTH_URL'],
	        	username=os.environ['OS_USERNAME'],
	        	password=os.environ['OS_PASSWORD'],
	        	project_name=os.environ['OS_PROJECT_NAME'],
	        	region_name='RegionOne',
	        	project_domain_name=os.environ['OS_USER_DOMAIN_NAME'],
	        	user_domain_name=os.environ['OS_USER_DOMAIN_NAME'],
	        	identity_api_version=3,
	        	image_api_version=2)
#
# compute
#	
	def getServerDetail(self):
		server_detail = []
	    	for server in self.conn.compute.servers():
			server_detail.append(server.to_dict())
		return server_detail

	def getFlavorList(self):
	        flavor_list = []
	        for flavor in self.conn.compute.flavors():
	                flavor_list.append(flavor.to_dict())
	        return flavor_list

	def getLimits(self):
		return self.conn.compute.get_limits()
#
# network
#
	
	def deleteAllFloatingIp(self):
		for floating_ip in self.conn.network.ips():
			self.conn.network.delete_ip(floating_ip)
		return

	def setExternalGateway(self, router_name, network_name):
		r = self.conn.network.find_router(router_name)
		n = self.conn.network.find_network(network_name)
		gateway_info = {'network_id':n.id}
		self.conn.network.update_router(r, external_gateway_info=gateway_info)
		return

	def unsetExternalGateway(self, router_name):
		r = self.conn.network.find_router(router_name)
		self.conn.network.update_router(r, external_gateway_info=None)
		return

	def deleteNetwork(self, network_name):
		n = self.conn.network.find_network(network_name)
		self.conn.network.delete_network(n, ignore_missing=False)
		return

	def createProviderNetwork(self, **options):
		network_attrs = {
			'router:external': True, 
			'provider:network_type': u'flat', 
			'name': 'provider', 
			'provider:physical_network': u'extnet', 
			'admin_state_up': True}
		if options.get("network_name") is not None:
			network_attrs['name'] = options['network_name']
		n = self.conn.network.create_network(**network_attrs)
		subnet_attrs = {
			'name':'provider_subnet', 
			'network_id':n.id, 
			'ip_version':'4',
			'cidr':'10.0.2.0/24', 
			'gateway_ip':'10.0.2.1', 
			'is_dhcp_enabled':False }
		
		if options.get("subnet_range") is not None:
			subnet_attrs['cidr'] = options['subnet_range']

		if options.get("gateway") is not None:
			subnet_attrs['gateway_ip'] = options['gateway']
		
		if options.get("allocation_pool") is not None:
			subnet_attrs['allocation_pools'] = options['allocation_pool']
		
		if options.get("dns_list") is not None:
			subnet_attrs['dns_nameservers'] = options['dns_list']
		
		sn = self.conn.network.create_subnet(**subnet_attrs)
		return

	def setSubnetDns(self, **options):
		if options.get("subnet_name") is not None:
			subnet_name = options['subnet_name']
		else:
			subnet_name = "self-service"

		if options.get("dns_list") is not None:
                        dns_list = options['dns_list']
		else:
			dns_list = []

		
		sn = self.conn.network.find_subnet(subnet_name)
		if sn is not None:
			self.conn.network.update_subnet(sn, dns_nameservers=dns_list)
		return

	def deleteAllPorts(self):
		for port in self.conn.network.ports():
        		print(port)


def getServerList():
	c = cmdWrapper("openstack server list")
	return c.loaded_json

def ip2long(ip):
    	packed = inet_aton(ip)
    	lng = struct.unpack("!L", packed)[0]
    	return lng

def getAvailableFloatingIpList():
	c = cmdWrapper("openstack floating ip list")
	filter_list = []
	for j in c.loaded_json:
		if j['Fixed IP Address'] is None:
			filter_list.append(j)

	sorted_list = sorted(filter_list, key=lambda f: ip2long(f['Floating IP Address']), reverse=False)
	return sorted_list

def getFloatingIp():
	available_ip = getAvailableFloatingIpList()
	
	if available_ip is not None and len(available_ip) > 0:
		out = "{\"floating_network_id\":\"" + available_ip[0]['Floating Network'] + "\"," + \
			"\"id\":\"" + available_ip[0]['ID'] + "\",\"project_id\":\"" + available_ip[0]['Project'] + "\"," + \
			"\"floating_ip_address\":\"" + available_ip[0]['Floating IP Address'] + "\"}"
		print out
	else:
		c = cmdWrapper("openstack floating ip create provider")
		print json.dumps(c.loaded_json)
	return

def getProviderSubnet():
	c = cmdWrapper("openstack subnet show provider_subnet")
	print json.dumps(c.loaded_json)
	return

def getServerDetail():
	server_list = getServerList()
	server_detail = []
	for server in server_list:
		c = cmdWrapper("openstack server show " + server['ID'])
		server_detail.append(c.loaded_json)
	return server_detail

def getServerDetailBySdk():
	s = sdkWorker()
	return s.getServerDetail()

def getVmList():
	print json.dumps(getServerDetail())
	return

def getVmListBySdk():
	server_detail = getServerDetailBySdk()
	if len(server_detail) > 0:
		print json.dumps(server_detail)
	return

def getHypervisorList():
	c1 = cmdWrapper("openstack hypervisor list")
	hypervisor_list = c1.loaded_json
	hypervisor_detail = []
	for hv in hypervisor_list:
		c2 = cmdWrapper("openstack hypervisor show " + str(hv['ID']))
		hypervisor_detail.append(c2.loaded_json)
	print json.dumps(hypervisor_detail)
	return

def getFlavorList():
	c = cmdWrapper("openstack flavor list")
	return c.loaded_json

def getFlavorListBySdk():
	s = sdkWorker()
        return s.getFlavorList()


def getProjectOverview():
	c = cmdWrapper("openstack limits show --absolute")
	absolute_info = c.loaded_json
	# Part 1 : Overall usage
	return_val =  "{\"overall\":["
	for val in absolute_info:
		if val['Name'] == "totalInstancesUsed" or \
			val['Name'] == "maxTotalInstances" or \
			val['Name'] == "totalCoresUsed" or \
			val['Name'] == "maxTotalCores" or \
			val['Name'] == "totalRAMUsed" or \
			val['Name'] == "maxTotalRAMSize":
			return_val +=  json.dumps(val) + ","
	return_val = return_val[:-1]
	return_val += "],"
	return_val +=  "\"servers\":["
	# Part 2 : Show usage by VM's flavor setting
	flavor_list = getFlavorList()
	server_detail = getServerDetail()
	if len(server_detail) > 0:
		for server in server_detail:
			return_val += "{\"Name\":\"" + server['name'] + "\",\"ID\":\"" + server['id'] + "\","
			temp = server['flavor'].split("(")
			flavor_id = temp[len(temp)-1]
			flavor_id = flavor_id[:-1]
			for flavor in flavor_list:
				if flavor_id == flavor['ID']:
					return_val += "\"VCPUs\":" + str(flavor['VCPUs']) + "," + "\"RAM\":" + str(flavor['RAM']) + "," + "\"Disk\":" + str(flavor['Disk']) 
			return_val += "},"
		
		return_val = return_val[:-1] + "]}"
	else:
		return_val += "]}"
	print return_val
	return

def getProjectOverviewBySdk():
	s = sdkWorker()

	absolute_info = s.getLimits().absolute
	# Part 1 : Overall usage
	return_val =  "{\"overall\":[" + \
                "{\"Name\": \"totalInstancesUsed\", \"Value\":" + str(absolute_info.instances_used) + "}," + \
                "{\"Name\": \"maxTotalInstances\", \"Value\":" + str(absolute_info.instances) + "}," + \
                "{\"Name\": \"totalCoresUsed\", \"Value\":" + str(absolute_info.total_cores_used) + "}," + \
                "{\"Name\": \"maxTotalCores\", \"Value\":" + str(absolute_info.total_cores) + "}," + \
                "{\"Name\": \"totalRAMUsed\", \"Value\":" + str(absolute_info.total_ram_used) + "}," + \
                "{\"Name\": \"maxTotalRAMSize\", \"Value\":" + str(absolute_info.total_ram) + "}],"

	return_val +=  "\"servers\":["
	# Part 2 : Show usage by VM's flavor setting
	flavor_list = s.getFlavorList()
	server_detail = s.getServerDetail()
	if len(server_detail) > 0:
		for server in server_detail:
			return_val += "{\"Name\":\"" + server['name'] + "\",\"ID\":\"" + server['id'] + "\","
			flavor_id = server['flavor']['id']
			for flavor in flavor_list:
				if flavor_id == flavor['id']:
					return_val += "\"VCPUs\":" + str(flavor['vcpus']) + "," + "\"RAM\":" + str(flavor['ram']) + "," + "\"Disk\":" + str(flavor['disk']) 
			return_val += "},"
		
		return_val = return_val[:-1] + "]}"
	else:
		return_val += "]}"
	print return_val
	return

def getProjectQuota():
	c = cmdWrapper("openstack quota show admin")
	print json.dumps(c.loaded_json)
	return 

def getUserList():
	c = cmdWrapper("openstack user list")
	print json.dumps(c.loaded_json)
	return 

def powerOnVm(vmId):
	c = cmdWrapper("openstack server start " + vmId, noreturn=True)
	print json.dumps(c.loaded_json)
	return

def deleteAllFloatingIp():
	c = cmdWrapper("openstack floating ip list")
	if len(c.loaded_json) > 0:
		cmd = "openstack floating ip delete "
		for ip in c.loaded_json:
			cmd += ip['Floating IP Address'] + " "
		cmdWrapper(cmd, noreturn=True)
	print json.dumps(c.loaded_json)
	return

def deleteAllFloatingIpBySdk():
	s = sdkWorker()
	s.deleteAllFloatingIp()
	return

def deleteAllPortsBySdk():
	s = sdkWorker()
	s.deleteAllPorts()
	return

def unsetExternalGateway():
	c = cmdWrapper("openstack router unset --external-gateway router", noreturn=True)
	print json.dumps(c.loaded_json)
	return

def unsetExternalGatewayBySdk():
	s = sdkWorker()
	s.unsetExternalGateway("router")
	return

def deleteProviderNetwork():
	deleteAllFloatingIp()
	unsetExternalGateway()
	c = cmdWrapper("openstack network delete provider", noreturn=True)
	print json.dumps(c.loaded_json)
	return

def deleteProviderNetworkBySdk():
	s = sdkWorker()
	s.deleteAllFloatingIp()
	s.unsetExternalGateway("router")
	s.deleteNetwork("provider")	
	return

def powerOffVm(vmId):
	c = cmdWrapper("openstack server stop " + vmId, noreturn=True)
	print json.dumps(c.loaded_json)
	return

def enableVm(vmId):
	c = cmdWrapper("openstack server unlock " + vmId, noreturn=True)
	print json.dumps(c.loaded_json)
	return

def disableVm(vmId):
	c = cmdWrapper("openstack server lock " + vmId, noreturn=True)
	print json.dumps(c.loaded_json)
	return

def getUserInfo(user):
	c = cmdWrapper("openstack user show " + user)
	print json.dumps(c.loaded_json)
	return 

def getVmInfo(vmId):
	c = cmdWrapper("openstack server show " + vmId)
	print json.dumps(c.loaded_json)
	return 

def deleteVm(vmId):
	c = cmdWrapper("openstack server delete " + vmId, noreturn=True)
	print json.dumps(c.loaded_json)
	return

def deleteFlavor(flavorId):
	c = cmdWrapper("openstack flavor delete " + flavorId, noreturn=True)
	print json.dumps(c.loaded_json)
	return

def getFlavorListAndDump():
	print json.dumps(getFlavorList())
	return

def getFlavorListAndDumpBySdk():
	flavor_list = getFlavorListBySdk()
	print json.dumps(flavor_list)
	return

def getImageList():
	c = cmdWrapper("openstack image list")
	print json.dumps(c.loaded_json)
	return 

def getNetworkList():
	c = cmdWrapper("openstack network list")
	print json.dumps(c.loaded_json)
	return 

def setQuota():
	format_check = sys.argv[2].isdigit() and sys.argv[3].isdigit() and sys.argv[4].isdigit()
	if format_check is True:
		if len(sys.argv) == 7:
                	c = cmdWrapper("openstack quota set --cores " + sys.argv[2] + " --instances " + sys.argv[3] + " --ram " + sys.argv[4] + \
                               " --volumes " + sys.argv[5] + " --gigabytes " + sys.argv[6] +  " admin ", noreturn=True)
			print json.dumps(c.loaded_json)
                else:
                        c = cmdWrapper("openstack quota set --cores " + sys.argv[2] + " --instances " + sys.argv[3] + " --ram " + sys.argv[4] + \
                               " admin ", noreturn=True)
			print json.dumps(c.loaded_json)
	else:
		printHelp()
	return

def setUserInfo():
	c = cmdWrapper("openstack user set --name \"" + sys.argv[2] + "\" --password " + sys.argv[3] + " --email " + sys.argv[4] + " " + sys.argv[5], noreturn=True)
	print json.dumps(c.loaded_json)
	return

def createProviderNetwork():
	dns_list_str = ""
	if len(sys.argv) == 7:
		dns_list = sys.argv[6].split(",")
		for dns in dns_list:
			dns_list_str += " --dns-nameserver " + dns
	c = cmdWrapper("openstack network create --external --provider-network-type flat --provider-physical-network extnet provider ")
	print json.dumps(c.loaded_json)
	cmd = "openstack subnet create --network provider --subnet-range " + sys.argv[2] + \
		" --gateway " + sys.argv[3] + " --no-dhcp --allocation-pool start=" + sys.argv[4] + ",end=" + sys.argv[5] + \
		dns_list_str + " provider_subnet"
	c2 = cmdWrapper(cmd)
	print json.dumps(c2.loaded_json)
	c3 = cmdWrapper("openstack router set --external-gateway provider router ", noreturn=True)
	print json.dumps(c3.loaded_json)
	c4 = cmdWrapper("openstack subnet set --no-dns-nameservers " + dns_list_str + " self-service_subnet ", noreturn=True)
	print json.dumps(c4.loaded_json)
	return

def createProviderNetworkBySdk():
	s = sdkWorker()
	pool = [{'start':sys.argv[4], 'end':sys.argv[5]}]
	if len(sys.argv) == 7:
		dns_list1 = []
                dns_list2 = sys.argv[6].split(",")
                for dns in dns_list2:
			dns_list1.append(dns)

		s.createProviderNetwork(network_name='provider', subnet_name="provider_subnet", subnet_range=sys.argv[2], gateway=sys.argv[3], 
			allocation_pool=pool, dns_list=dns_list1)
		s.setSubnetDns(subnet_name="self-service_subnet", dns_list=dns_list1)
	else:
		s.createProviderNetwork(network_name='provider', subnet_name="provider_subnet", subnet_range=sys.argv[2], gateway=sys.argv[3], 
			allocation_pool=pool)

	s.setExternalGateway("router", "provider")
	return

def createVm():
	c = cmdWrapper("openstack server create --flavor " + sys.argv[2] + " --image " + sys.argv[3] + \
		" --nic " + sys.argv[4] + " --key-name \"" + sys.argv[5] + "\" \"" + sys.argv[6] + "\"")
	print json.dumps(c.loaded_json)
	return

def resizeVm():
	c = cmdWrapper("openstack server resize --flavor " + sys.argv[2] + " " + sys.argv[3], noreturn=True)
	print json.dumps(c.loaded_json)
	return

def confirmResizeVm(vmId):
	c = cmdWrapper("openstack server resize --confirm " + vmId, noreturn=True)
	print json.dumps(c.loaded_json)
	c = cmdWrapper("openstack server reboot " + vmId, noreturn=True)
	print json.dumps(c.loaded_json)
	return

def setVmName():
	c = cmdWrapper("openstack server set --name \"" + sys.argv[2] + "\" \"" + sys.argv[3] + "\"", noreturn=True)
	print json.dumps(c.loaded_json)
	return

def createFlavor():
	c = cmdWrapper("openstack flavor create --id " + sys.argv[2] + " --ram " + sys.argv[3] + " --disk " + sys.argv[4] + " --vcpus " + sys.argv[5] + " " + sys.argv[6])
	print json.dumps(c.loaded_json)
	return

def associateFloatingIp():
	c = cmdWrapper("openstack server add floating ip " + sys.argv[2] + " " + sys.argv[3], noreturn=True)
	print json.dumps(c.loaded_json)
	return

def deassociateFloatingIp():
	c = cmdWrapper("openstack server remove floating ip " + sys.argv[2] + " " + sys.argv[3], noreturn=True)
	print json.dumps(c.loaded_json)
	return

def deleteFloatingIp():
	cmd = "openstack floating ip delete "
	for x in range(2, len(sys.argv)):
		cmd += sys.argv[x] + " "
	c = cmdWrapper(cmd, noreturn=True)
	print json.dumps(c.loaded_json)
	return

def isFloat(value):
	try:
		float(value)
		return True
	except ValueError:
		return False

def prettyTableToJson(inString):
	s_list = inString.split("\n")
	count=0
	keys = []
	json_out_str = "["
	for s in s_list:
		count += 1
		if count > 2:
			if len(s) > 0 and s[0] == '|':
				data = s.split("|")
				data.pop()
				del data[0]
				json_out_str += "{"
				count2 = 0
				for k in keys:
					json_out_str += "\"" + k + "\":"
					data[count2] = data[count2].lstrip().rstrip()
					if data[count2].isdigit() is True or isFloat(data[count2]) is True:
						json_out_str += data[count2] + ","
					else:
						json_out_str += "\"" + data[count2] + "\","
					count2 += 1
				json_out_str = json_out_str[:-1] + "},"
		elif count == 2:
			temp = s.split("|")
			for k in temp:
				keys.append(k.lstrip().rstrip())
			keys.pop()
			del keys[0]
				
	json_out_str = json_out_str[:-1] + "]"
	return json_out_str

def getCeilometerStatistics(resource_id, meter, period):
	if period.isdigit() is False:
		printHelp()
		return ""
	cmd = "ceilometer statistics -q resource_id=" + resource_id + " -m " + meter + " -p " + period
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE ,shell=True)
        out, err = p.communicate()
	return prettyTableToJson(out)

def getVncConsole(vmId):
	cmd = "nova get-vnc-console " + vmId + " novnc"
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE ,shell=True)
        out, err = p.communicate()
	print prettyTableToJson(out)
	return

def getNetworkStatistics():
	if sys.argv[3].isdigit() is False:
		printHelp()
		return
	p1 = subprocess.Popen("ceilometer resource-list ", stdout=subprocess.PIPE ,shell=True)
       	out1, err1 = p1.communicate()
	r_list = out1.split("\n")
	full_resource_id = ""
	for l in r_list:
		if len(l) > 0 and l[0] == '|':
			sub_list = l.split("|")
			if "instance-" in sub_list[1] and sys.argv[2] in sub_list[1]:
				full_resource_id = sub_list[1].lstrip()
				break
	out = "{\"incoming\":"
	out += getCeilometerStatistics(full_resource_id, "network.incoming.bytes.rate", sys.argv[3])
	out += ",\"outgoing\":"
	out += getCeilometerStatistics(full_resource_id, "network.outgoing.bytes.rate", sys.argv[3])
	out += "}"
	print out
	return

def getCpuUsageStatistics():
	print getCeilometerStatistics(sys.argv[2], "cpu_util", sys.argv[3])
	return

def getDiskUsageStatistics():
	print getCeilometerStatistics(sys.argv[2], "disk.usage", sys.argv[3])
	return

def getMemoryUsageStatistics():
	print getCeilometerStatistics(sys.argv[2], "memory.resident", sys.argv[3])
	return

def argMapping2(argument):
	switcher = {
		"--vmlist" : getVmListBySdk,
		"--overview" : getProjectOverviewBySdk,
		"--getquota" : getProjectQuota,
		"--getuserlist" : getUserList,
		"--getflavorlist" : getFlavorListAndDumpBySdk,
		"--getimagelist" : getImageList,
		"--getnetworklist" : getNetworkList,
		"--unsetexternalgateway" : unsetExternalGatewayBySdk,
		"--deleteprovidernetwork" : deleteProviderNetworkBySdk,
		"--deleteallfloatingip" : deleteAllFloatingIpBySdk,
		"--deleteallports" : deleteAllPortsBySdk,
		"--getfloatingip" : getFloatingIp,
		"--getavailablefloatingiplist" : getAvailableFloatingIpList,
		"--getprovidersubnet" : getProviderSubnet,
		"--gethypervisorlist" : getHypervisorList
	}
	func = switcher.get(argument, None)
	if func is not None:
		return func()
	else:
		printHelp()
	return

def argMapping3(argument):
	switcher = {
		"--poweronvm"  : powerOnVm,
		"--poweroffvm" : powerOffVm,
		"--enablevm"   : enableVm,
		"--confirmresizevm"  : confirmResizeVm,
		"--disablevm"  : disableVm,
		"--getuserinfo"  : getUserInfo,
		"--getvminfo"  : getVmInfo,
		"--getvncconsole"  : getVncConsole,
		"--deletevm"  : deleteVm,
		"--deleteflavor"  : deleteFlavor
	}
	func = switcher.get(argument, None)
	if func is not None:
		return func(sys.argv[2])
	else:
		printHelp()
	return

def argMapping4(argument):
	switcher = {
		"--associatefloatingip"  : associateFloatingIp,
		"--deassociatefloatingip"  : deassociateFloatingIp,
		"--getnetworkstatistics"  : getNetworkStatistics,
		"--getcpuusagestatistics"  : getCpuUsageStatistics,
		"--getmemoryusagestatistics"  : getMemoryUsageStatistics,
		"--getdiskusagestatistics"  : getDiskUsageStatistics,
		"--resizevm"  : resizeVm,
		"--setvmname"  : setVmName
	}
	func = switcher.get(argument, None)
	if func is not None:
		return func()
	else:
		printHelp()
	return

def argMapping5(argument):
	switcher = {
		"--setquota" : setQuota
	}
	func = switcher.get(argument, None)
	if func is not None:
		return func()
	else:
		printHelp()
	return

def argMapping6(argument):
	switcher = {
		"--setuserinfo" : setUserInfo,
		"--createprovidernetwork" : createProviderNetworkBySdk,
	}
	func = switcher.get(argument, None)
	if func is not None:
		return func()
	else:
		printHelp()
	return

def argMapping7(argument):
	switcher = {
		"--createflavor" : createFlavor,
		"--setquota" : setQuota,
		"--createprovidernetwork" : createProviderNetworkBySdk,
		"--createvm" : createVm
	}
	func = switcher.get(argument, None)
	if func is not None:
		return func()
	else:
		printHelp()
	return

def printHelp():
	print "Usage:"
	print "	--getfloatingip		Create an floating ip address from default provider network."
	print "	--getprovidersubnet	Get current subnet detail of default provider network."
	print "	--deleteallports	Delete all ports."
	print "	--deleteprovidernetwork	Delete default provider network."
	print "	--getquota		Get project quota."
	print "	--getflavorlist		Get flavor list."
	print "	--getimagelist		Get image list."
	print "	--getnetworklist	Get network list."
	print "	--getuserlist		Get user list."
	print "	--gethypervisorlist	Get hypervisor list."
	print "	--overview		Get overview information.Which are VM usage, vCPU usage and memory usage."
	print "	--unsetexternalgateway	Unset default external gateway."
	print "	--vmlist		Get VM(Intance) list."
	print ""
	print "	--confirmresizevm <ID>	Confirm resizing action of indicated VM(Instance)."
	print "	--deletevm <ID>		Delete indicated VM(Instance)."
	print "	--deleteflavor <ID>	Delete indicated flavor."
	print "	--disablevm <ID>	Disable VM(Instance) by indicated ID."
	print "	--enablevm <ID>		Enable VM(Instance) by indicated ID."
	print "	--getuserinfo <Name>	Get user information by indicated name."
	print "	--getvncconsole <ID>	Get vnc console by indicated VM ID."
	print "	--getvminfo <ID>	Get VM information by indicated VM ID."
	print "	--poweronvm <ID>	Power on VM(Instance) by indicated ID."
	print "	--poweroffvm <ID>	Power off VM(Instance) by indicated ID."
	print ""
	print "	--associatefloatingip <ID> <IP>"
	print "				Associating given floating ip to indicated VM(Instance)."
	print "	--deassociatefloatingip <ID> <IP>"
	print "				De-associating given floating ip to indicated VM(Instance)."
	print "	--getcpuusagestatistics <ID> <PERIOD>"
	print "				Get VM(instance) cpu usage statistics data by indicated ID.Unit of <PERIOD> is second."
	print "	--getdiskusagestatistics <ID> <PERIOD>"
	print "				Get VM(instance) disk usage statistics data by indicated ID.Unit of <PERIOD> is second."
	print "	--getmemoryusagestatistics <ID> <PERIOD>"
	print "				Get VM(instance) memory usage statistics data by indicated ID.Unit of <PERIOD> is second."
	print "	--getnetworkstatistics <ID> <PERIOD>"
	print "				Get VM(instance) network statistics data by indicated ID.Unit of <PERIOD> is second."
	print "	--resizevm <Flavor> <ID>"
	print "				Resizing VM by flavor.<Flavor>: Flavor ID, <ID>: VM ID."
	print "	--setvmname <Newname> <ID>"
	print "				Change VM Name.<Newname>: New name. <ID>: VM ID."
	print ""
	print "	--setquota <Core> <Instance> <RAM> (<VOLUME> <GIGABYTE>)"
	print "				Set project quota.Input parameters must be intergers and with order: <Core> <Instance> <RAM> <VOLUME> <GIGABYTE>."
	print ""
	print "	--createprovidernetwork <Range> <Gateway> <Start> <End> (<DNS>)"
	print "				Create provider network." 
	print "				<Range>: e.g. 192.168.43.0/24"
	print "				<Gateway>: e.g. 192.168.43.1" 
	print "				<Start>: e.g. 192.168.43.100."
	print "				<End>: e.g. 192.168.43.150."
	print "				<DNS>: optional. e.g. 8.8.8.8,10.10.10.10."
	print "	--setuserinfo <Name> <Password> <Email> <User>"
	print "				Set user information. Input parameters must be order: <Name> <Password> <Email> <User>."
	print ""
	print "	--createvm <Flavor> <Image> <Nic> <KeyPair> <Name>"
	print "				Create VM. <Flavor>: Flavor ID, <Image>: Image ID, "
	print "				<Nic>: NIC configuration info, format: net-id=net-uuid,v4-fixed-ip=ip-addr,v6-fixed-ip=ip-addr,port-id=port-uuid "
	print "				<KeyPair>: KeyPair Name."
	print "				<Name>: VM Name."
	print "	--createflavor <Flavor> <Ram> <Disk> <VCPU> <Name>"
	print "				Create flavor. <Flavor>: Flavor ID(UUID), <Ram>: Ram size(MB), <Disk>: Disk size(GB), "
	print "				<VCPU>: Number of VCPUs, <Name>: Flavor name."
	print ""
	print "	--deletefloatingip <IP1> <IP2> ...."
	print "				Delete floating ips"
	return

if __name__ == "__main__":
	if len(sys.argv) == 1:
		printHelp()
	elif sys.argv[1] != "--deletefloatingip":
		switcher = {
			2 : argMapping2,
			3 : argMapping3,
			4 : argMapping4,
			5 : argMapping5,
			6 : argMapping6,
			7 : argMapping7
		}
		func = switcher.get(len(sys.argv), None)
		if func is not None:
			func(sys.argv[1])
		else:
			printHelp()
	else:
		if len(sys.argv) > 2:
			deleteFloatingIp()
		else:
			printHelp()

