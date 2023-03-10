[![Python application](https://github.com/thenodon/fortigate-exporter-discovery//actions/workflows/python-app.yml/badge.svg)](https://github.com/thenodon/fortigate-exporter-discovery//actions/workflows/python-app.yml)
[![PyPI version](https://badge.fury.io/py/fortigate-exporter-discovery.svg)](https://badge.fury.io/py/fortigate-exporter-discovery)

fortigate-exporter-discovery
------------------------
# Overview

The fortigate-exporter-discovery is a Prometheus file discovery tool that use a Fortimanager instance
to get fortigate's based on a adom.

The tool work with the [fortigate-exporter](https://github.com/bluecmd/fortigate_exporter).
> It requires that the following pull request is accepted https://github.com/bluecmd/fortigate_exporter/pull/206 or 
> you can use https://github.com/thenodon/fortigate_exporter. 

# Configuration

The configuration file include the credentials for the Fortimanager and the configuration for each adom.
> The `token` used for the Fortigate api access should be the same for all Fotigate in the same adom.

Example:

```yaml
fmg:
  # The host name of the fmg - 
  host: "https://fmg.foo.com"
  username: fmg_foo
  password: fmg_foo_password

  adoms:
    - name: SDWAN_Foo
      # Same api key for all fortigate in the same adom
      #apikey: XYZ
      #port: 44343
      # Additional labels
      labels:
        customer: Foo
      # This is common for all fortigates in the same adom
      fortigate:
        token: XYZ
        port: 44343
        # Profile is a named entry in fortigate-exporter fortigate-key.yaml file to get probes exclude/includes
        profile: common
```

Two environment variables must be set.

- FMG_DISCOVERY_CONFIG - the path to the above config file, default is ./config.yml
- FMG_PROMETHEUS_SD_FILE_DIRECTORY - the output directory for the file discovery files used in the your Prometheus
configuration. Each adom will have its own file.


# Run 

```shell
pip install fortigate-exporter-discovery
FMG_DISCOVERY_CONFIG=config.yml
FMG_PROMETHEUS_SD_FILE_DIRECTORY=/etc/prometheus/file_sd/fortigate
python -m fmg_discovery
```


