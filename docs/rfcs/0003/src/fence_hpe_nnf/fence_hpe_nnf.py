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
        # In the case that we want to allow the agent to recover the Rabbit,
        # Update the Storage CR to show healthy for this node and
        # remove the logged error below
    	logging.error("Power on disallowed for this node\n")
	else:
        #TODO: Update Storage CR here, Node name will be in the pcmk_host_list
        pass

	return

def reboot_cycle(conn, options):
	"""
	Ignores power cycle requests
	"""

	logging.error("Reboots disallowed for this node\n")

	return False

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
	docs["shortdesc"] = "Fence agent for HPE NNF Node via Kubernetes Storage CR"
	docs["longdesc"] = "fence_hpe_nnf is a fence agent that marks a specific NNF Node as degraded by \
updating the Storage CR via the Kubernetes API.  It will report node status by connecting to the HSS and querying redfish.\n"
	docs["vendorurl"] = "http://www.hpe.com"
	docs["symlink"] = [("fence_hpe_nnf", "Fence agent for HPE NNF Node via Kubernetes Storage CR")]
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
