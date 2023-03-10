from typing import Dict, Any


class Fortigate:
    def __init__(self, name: str, ip: str):
        self.name: str = name
        self.ip: str = ip
        self.token: str = ''
        self.port: int = 8443
        self.labels: Dict[str, str] = {}
        self.profile: str = ''

    def as_labels(self) -> Dict[str, str]:

        labels = self.labels.copy()
        if self.token:
            labels['token'] = self.token
        if self.profile:
            labels['profile'] = self.profile
        return labels

    def as_prometheus_file_sd_entry(self) -> Dict[str, Any]:
        return {'target': [f"https://{self.ip}:{self.port}"], 'labels': self.as_labels()}

