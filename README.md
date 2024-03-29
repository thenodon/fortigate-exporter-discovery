[![Python application](https://github.com/thenodon/fortigate-exporter-discovery//actions/workflows/python-app.yml/badge.svg)](https://github.com/thenodon/fortigate-exporter-discovery//actions/workflows/python-app.yml)
[![PyPI version](https://badge.fury.io/py/fortigate-exporter-discovery.svg)](https://badge.fury.io/py/fortigate-exporter-discovery)

fortigate-exporter-discovery
------------------------
# Overview

The fortigate-exporter-discovery is a Prometheus discovery tool that use a Fortimanager instance
to get fortigate's based on adoms. 
It works both for file and http service discovery.

The tool can also work as an exporter for metrics related to the relation between a Fortimanager and its Fortigate's.
This is only supported when run in `server` mode.

The tool work with the [fortigate-exporter](https://github.com/bluecmd/fortigate_exporter).
> It requires that the following pull request is accepted https://github.com/bluecmd/fortigate_exporter/pull/206 or 
> you can use https://github.com/thenodon/fortigate_exporter. 

# Labels naming (since 0.5.0)
All labels are returned prefixed as `__meta_fortigate_`

# Configuration

The configuration file include the credentials for the Fortimanager and the configuration for each adom.
> The `token` used for the Fortigate api access should be the same for all Fotigate in the same adom.

Example:

```yaml
fmg:
  # The url, username and password of the Fortimanager  
  host: "https://fmg.foo.com"
  username: fmg_foo
  password: fmg_foo_password

  adoms:
    - name: SDWAN_Foo
      # Additional labels that will be added to all metrics
      labels:
        customer: Foo
      # This is common for all Fortigates in the same adom
      fortigate:
        # The api token of the Fortigates
        token: XYZ
        # The port where the Fortigates expose the API
        port: 44343
        # Profile is a named entry in fortigate-exporter fortigate-key.yaml file to get probes exclude/includes
        profile: common
```

Two environment variables must be set.

- FMG_DISCOVERY_CONFIG - the path to the above config file, default is `./config.yml`
- FMG_DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY - the output directory for the file discovery files used in your Prometheus
configuration. Each adom will have its own file.
- FMG_DISCOVERY_LOG_LEVEL - the log level, default `WARNING`
- FMG_DISCOVERY_LOG_FILE - the log file, default `stdout`
- FMG_DISCOVERY_HOST - the ip to expose the exporter on, default `0.0.0.0` - only applicable if running in server mode
- FMG_DISCOVERY_PORT - the port to expose the exporter on, default `9693`
- FMG_DISCOVERY_BASIC_AUTH_ENABLED - use basic auth if set to anything, default `false`
- FMG_DISCOVERY_BASIC_AUTH_USERNAME - the username 
- FMG_DISCOVERY_BASIC_AUTH_PASSWORD - the password 
- FMG_DISCOVERY_CACHE_TTL - the ttl in seconds to keep the result from Fortimanager in cache, default `60`

> FMG_DISCOVERY_CACHE_TTL is a measure to secure the Fortimanager from an api request storm.

# Run 

## File service discovery
```shell
pip install fortigate-exporter-discovery
FMG_DISCOVERY_CONFIG=config.yml
FMG_DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY=/etc/prometheus/file_sd/fortigate
python -m fmg_discovery
```

## Http service discovery
```shell
pip install fortigate-exporter-discovery
FMG_DISCOVERY_CONFIG=config.yml
FMG_DISCOVERY_BASIC_AUTH_ENABLED=true
FMG_DISCOVERY_BASIC_AUTH_USERNAME=foo
FMG_DISCOVERY_BASIC_AUTH_PASSWORD=bar
FMG_DISCOVERY_LOG_LEVEL=INFO
python -m fmg_discovery --server
```
Test discovery by curl

```shell
curl -ufoo:bar localhost:9693/prometheus-sd-targets
```

Test exporter by curl

```shell
curl -ufoo:bar localhost:9693/metrics
# HELP fmg_conf_status Configuration status 1==insync 0==all other states
# TYPE fmg_conf_status gauge
....
# HELP fmg_conn_status Connection status 1==up 0==all other states
# TYPE fmg_conn_status gauge
....
# HELP fmg_conn_mode Connection mode 1==active 0==all other states
# TYPE fmg_conn_mode gauge
....

```

# Prometheus job configuration

Example:

```yaml
  - job_name: 'fortigate_exporter'
    metrics_path: /probe
    file_sd_configs:
      - files:
          - /etc/prometheus/file_sd/fortigate/*.yml
    params:
      # If profile is not part of your labels from the discovery
      profile:
      - fs124e
    relabel_configs:
      - source_labels:
          - __meta_fortigate_name
        action: replace
        target_label: name
      - source_labels:
          - __meta_fortigate_zone
        action: replace
        target_label: zone
      - source_labels:
          - __meta_fortigate_adom
        action: replace
        target_label: adom
      - source_labels:
          - __meta_fortigate_latitude
        action: replace
        target_label: latitude
      - source_labels:
          - __meta_fortigate_longitude
        action: replace
        target_label: longitude
      - source_labels:
          - __meta_fortigate_platform
        action: replace
        target_label: platform    

      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__meta_fortigate_token]
        target_label: __param_token
      - source_labels: [__param_target]
        regex: '(?:.+)(?::\/\/)([^:]*).*'
        target_label: instance
      - target_label: __address__
        replacement: '[::1]:9710'
      
```
Make sure to use the last labeldrop on the `token` label so that the tokens is not be part of your time series.
> Since `token` is a label it will be shown in the Prometheus webgui at `http://<your prometheus>:9090/targets`.
>
> **Make sure you protect your Prometheus if you add the token part of your prometheus config**
>
> Some options to protect Prometheus:
> - Only expose UI to localhost --web.listen-address="127.0.0.1:9090"
> - Basic authentication access - https://prometheus.io/docs/guides/basic-auth/
> - It is your responsibility!


