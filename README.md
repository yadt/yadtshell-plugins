# yadtshell-plugins

## Installation
Build a software package with [PyBuilder](http://pybuilder.github.io) and install it.

## f5 rest loadbalancer plugin

Abstract a loadbalancer as a host-local service.
TLDR:
* Service up    -> Node is in the loadbalancer and receives traffic
* Service down  -> Node is disabled and will not receive traffic
* Start service -> Enable node in loadbalancer
* Stop service  -> Disable node in loadbalancer

### Configuration
Use your configuration management solution to deliver the following file : 

`/etc/yadtshell/loadbalancerservice.py`
```python
import yadtshell

IMPLEMENTATION = 'yadtshell_plugins.f5'

RESTAPI_USERNAME = 'f5-user-name'
RESTAPI_PASSWORD = 'f5-password'
LTM_PARTITION = '~ltm_partition_you_use~'

CLUSTERS = {
    'lb-cluster-1' : ['1.3.3.7', '1.3.3.8'],
    'lb-cluster-2': ['1.2.3.4', '2.3.4.5'],
}
TRIES = 3
WAIT_SECONDS = 5.0
```

Notes:
* A cluster of loadbalancers will require state changes to propagate to each 
  loadbalancer. For example enabling a node in the loadbalancer cluster
  `lb-cluster-1` will send REST calls against the load balancers at `1.3.3.7` 
  and `1.3.3.8` and also check the status on both of those.
* The `LTM_PARTITION` declaration can be left empty if you are using the 
  default partition.
* The `IMPLEMENTATION` is a leftover from an earlier SOAP implementation.
  REST is much more powerful and lightweight, which is why the SOAP 
  implementation is not included anymore.

### Usage

Now you can use the following snippet in a `yadt.conf.d` directory:

```yaml
services:
    my_load_balancer: # name is arbitrary
        class: yadtshell_plugins.services.LB
        implementation: yadtshell_plugins.f5rest
        is_frontservice: true
        loadbalancer_clusters: ['lb-cluster-1', 'lb-cluster-2']
        needs_services: [monitoring]
        status_max_tries: 5
```

Where:
* `status_max_tries` is the amount of retries after a state change until the 
  new state is reflected by every load balancer in the cluster. Since the 
  F5 REST-API does not seem to be synchronous this is necessary.

## livestatus service plugin


Abstract monitoring as a host-local service.
TLDR:
* Service up    -> Host and service alarms for this host are enabled
* Service down  -> Host and service alarms for this host are muted (
  DISABLE_NOTIFICATIONS)
* Start service -> Enable host and service alarms for this host
* Stop service  -> Disable host and service alarms for this host

### Setup
Any mk-livestatus capable monitoring solution ([shinken](http://www.shinken-monitoring.org/wiki/livestatus_shinken), [icinga](http://docs.icinga.org/latest/en/int-mklivestatus.html), [nagios](http://mathias-kettner.de/checkmk_livestatus.html)) with [mk-livestatus](http://mathias-kettner.de/checkmk_livestatus.html) and [livestatus-service](https://github.com/ImmobilienScout24/livestatus_service) installed.

### Configuration
Use your configuration management solution to deliver the following file : 

`/etc/yadtshell/livestatusservice.py`
```python
import yadtshell

SERVERS = {
}
```
`SERVERS` is a mapping of stage => server but this [only works with the ImmobilienScout24 host name schema right now](https://github.com/yadt/yadtshell/blob/master/src/main/python/yadtshell/util.py#L47) so you'll have to specify the server to use on a per-host basis (see below). Or fix it ;-)

### Usage
Now you can use the following snippet in a `yadt.conf.d` directory:

```yaml
services:
    monitoring:
        class: yadtshell_plugins.services.LivestatusService
        livestatus_server: your-monitoring-server.domain
```
Of course you should also create a dependency so that this service is actually started and stopped when adequate.
A common use case if you're also load balancing is to have the load balancing service depend on the monitoring service (`needs_services: ["monitoring"]`) and then have the monitoring service depend on your app (`needs_service: ["tomcat-or-httpd-or-whatever-container-you-use"]`)
