pcs stonith create stonith-rabbit-node-1 fence_nnf pcmk_host_list=rabbit-node-1 kubernetes-service-host=10.30.107.247 kubernetes-service-port=6443 service-token-file=/etc/nnf/service.token service-cert-file=/etc/nnf/service.cert nnf-node-name=rabbit-node-1 verbose=1

pcs stonith create stonith-rabbit-compute-2 fence_redfish pcmk_host_list="rabbit-compute-2" ip=10.30.105.237 port=80 systems-uri=/redfish/v1/Systems/1 username=root password=REDACTED ssl_insecure=true verbose=1

pcs stonith create stonith-rabbit-compute-3 fence_redfish pcmk_host_list="rabbit-compute-3" ip=10.30.105.253 port=80 systems-uri=/redfish/v1/Systems/1 username=root password=REDACTED ssl_insecure=true verbose=1