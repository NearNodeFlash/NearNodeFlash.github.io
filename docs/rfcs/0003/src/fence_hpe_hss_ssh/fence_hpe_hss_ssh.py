#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright 2021, 2022 Hewlett Packard Enterprise Development LP
# Other additional copyright holders may be indicated within.
#
# The entirety of this work is licensed under the Apache License,
# Version 2.0 (the "License"); you may not use this file except
# in compliance with the License.
#
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, re, time
import atexit
from os.path import exists

sys.path.append("@FENCEAGENTSLIBDIR@")

# In some cases, we do not wish to allow power off
allow_powerOff = False

try:
	from fencing import *
	from fencing import fail, EC_STATUS
except:
	if exists("/usr/share/fence/fencing.py"):
		sys.path.append("/usr/share/fence/")
		try:
			from fencing import *
			from fencing import fail, EC_STATUS
		except:
			fence_import_error()
	else:
		fence_import_error()
		

def fence_import_error():
	print("Error importing fencing libs, may need to update python path")
	print("e.g. export PYTHONPATH=/usr/share/fence/")
	exit(1)

def get_power_status(conn, options):
	"""
	Checks the power state of node 0

	Returns:
	"on" - Node 0 is powered on
	"off" - Any power state other than ON
	"""

	# TODO: Perhaps drive this off of pmck_host_map
	conn.send_eol("redfish node status | grep 'node 0'")

	re_state = re.compile('\[(.*)', re.IGNORECASE)
	conn.log_expect(re_state, int(options["--shell-timeout"]))

	status = conn.match.group(1).lower()

	if status.startswith("on"):
		return "on"
	else:
		return "off"

def set_power_status(conn, options):
	"""
	Sets the power state of Node 0 to 'on' or 'off'
	"""

	if options["--action"] == "on":
		conn.send_eol("redfish node 0 on")
	else:
		if allow_powerOff:
			conn.send_eol("redfish node 0 forceoff")

	conn.log_expect(options["--command-prompt"], int(options["--power-timeout"]))

	return

def reboot_cycle(conn, options):
	"""
	Powers off the node (it does not actually power cycle)
	"""

	conn.send_eol("redfish node 0 forceoff")
	conn.log_expect(options["--command-prompt"], int(options["--power-timeout"]))

	if get_power_status(conn, options) == "off":
		logging.error("Timed out waiting to power ON\n")

	return True

# From the HSS redfish utility
# nC usage:
# redfish node status
# redfish node [0-3] [on|off|forceoff]

def main():
	"""
	Agent entry point
	"""

	device_opt = ["ipaddr", "login", "passwd", "cmd_prompt", "secure"]

	atexit.register(atexit_handler)

	all_opt["cmd_prompt"]["default"] = ["nC-RBTP:>"]
	all_opt["power_wait"]["default"] = 5

	options = check_input(device_opt, process_input(device_opt))

	docs = {}
	docs["shortdesc"] = "Fence agent for HPE HSS over SSH"
	docs["longdesc"] = "fence_hpe_hss_ssh is a fence agent that connects to the HSS device. It logs into \
device via ssh and interacts with a specific node.\n"
	docs["vendorurl"] = "http://www.hpe.com"
	docs["symlink"] = [("fence_hpe_hss_ssh", "Fence agent for HPE HSS over SSH")]
	show_docs(options, docs)

	##
	## Operate the fencing device
	####
	conn = fence_login(options)

	result = fence_action(conn, options, set_power_status, get_power_status, get_power_status)

	fence_logout(conn, "exit")
	sys.exit(result)

if __name__ == "__main__":
	main()
