import os
import yaml
from fmg_discovery.fmg_api import FMG
from typing import Dict, Any, List

FMG_DISCOVERY_CONFIG = 'FMG_DISCOVERY_CONFIG'
FMG_PROMETHEUS_SD_FILE_DIRECTORY = 'FMG_PROMETHEUS_SD_FILE_DIRECTORY'

if __name__ == "__main__":
    if not os.getenv(FMG_PROMETHEUS_SD_FILE_DIRECTORY):
        print(f"Env FMG_PROMETHEUS_SD_FILE_DIRECTORY must be set to a existing directory path")
        exit(1)
    if not os.path.exists(os.getenv(FMG_PROMETHEUS_SD_FILE_DIRECTORY)):
        print(f"Directory {FMG_PROMETHEUS_SD_FILE_DIRECTORY} does not exists")
        exit(1)
    with open(os.getenv(FMG_DISCOVERY_CONFIG, 'config.yml'), 'r') as config_file:
        try:
            # Converts yaml document to python object
            config = yaml.safe_load(config_file)

        except yaml.YAMLError as err:
            print(err)

    fmg = FMG(config)
    fws = fmg.get_fmg_devices()

    prometheus_file_sd: Dict[str, List[Any]] = {}
    for adom_name, fws in fws.items():
        for fw in fws:

            if adom_name not in prometheus_file_sd:
                prometheus_file_sd[adom_name] = []
            prometheus_file_sd[adom_name].append(fw.as_prometheus_file_sd_entry())

        with open(f"{os.getenv(FMG_PROMETHEUS_SD_FILE_DIRECTORY)}/{adom_name}.yaml", 'w') as config_file:
            try:
                # Converts yaml document to python object
                config = yaml.safe_dump(prometheus_file_sd[adom_name], config_file)
            except yaml.YAMLError as err:
                print(err)

    # Generate
    print("hello")
