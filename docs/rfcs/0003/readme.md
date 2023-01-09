---
authors: Bill Johnson <billj@hpe.com>
state: discussion
discussion: 
---
GFS2 Cluster Fencing Agents
==================================
The GFS2 file systems requires a cluster in order to avoid split-brained behavior when 2 or more nodes are accessing the file system.  In order to achieve this, NNF makes use of a Pacemaker Cluster in combination with CoroSync for inter-node communication.  This cluster requires fencing agents to be defined for each node in the cluster.  These agents are responsible for "fencing" off a node that has been "voted off of the island".

In the Near Node Flash (Rabbit) System, there are 2 types of nodes in a PCS Cluster:
* 1 Rabbit Node
* Upto 16 Compute Nodes
Note: In a given chassis it is expected that the Rabbit and all 16 compute nodes are part of a cluster.  There may be exceptions for UAN/FEN nodes in a given chassis, they may be exempted from the cluster.

There are a number of different approaches to fencing misbehaving nodes:
* Power the node off - This is the typical approach to fencing
* Do nothing and report the node
* Mark the node in some way as unhealthy

After a bit of discussion with our customer it has been decided that we will mark a misbehaving node as degraded within Kubernetes.  We have engineered the Storage object Spec section to expose a region where nodes may be marked as degraded by a fencing agent.  The basic flow is as follows:

1. The cluster achieves a quorum that a specific node is to be fenced.
2. The node assigned to fence the offending node calls the fencing agent running on that node, passing it the name of the node to be fenced.
3. The fencing agent queries the Storage object via the Kubernetes API.
4. The fencing agent marks the node as Degraded in the Spec and updates the Storage object via the Kubernetes API.

It is the responsibility of the WLM, Flux in this case, to watch for these changes and to take the appropriate action.  In the case of Rabbit, this may mean removing the Rabbit from the schedule and allowing any remaining jobs to complete/drain.  Ultimately it may require an administrator to analyze the degraded Rabbit for any malfunctions before it can be placed back into service.

Sample Agents
==================================
Contained within this RFC are 2 sample fencing agents.  Both agents are written in python3 and require the fencing.py python module in order to function.

## fence_hpe_hss_ssh

**fence_hpe_hss_ssh** is a fencing agent that connects to the HSS via SSH and can power a node on or off using the redfish tool present on the managing HSS.  This fencing agent is basically functional and will install and run in a Pacemaker cluster.

## fence_hpe_nnf
 
**fence_hpe_nnf** is a fencing agent that is intended to mark an NNF node as Degraded in the Storage CR, **it will not power down a node that has been selected for fencing**.  At the time of this writing, this fencing agent only has the structure framed in and is awaiting the specific kubernetes objects and logic in order to become functional.