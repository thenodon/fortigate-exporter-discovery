from typing import Dict, List

from prometheus_client.registry import Collector, Metric

from fmg_discovery.fmg_metrics import FmgMetrics
from fmg_discovery.fw import Fortigate


def to_list(metric_generator) -> List[Metric]:
    metrics = []
    for metric in metric_generator:
        if metric.samples:
            # Only append if the metric has a list of Samples
            metrics.append(metric)
    return metrics


class FmgCollector(Collector):
    def __init__(self, fws: Dict[str, List[Fortigate]]):
        self.fws = fws

    async def collect(self):
        all_module_metrics = []
        transformer = FmgMetrics(self.fws)
        transformer.parse()
        t = to_list(transformer.metrics())
        all_module_metrics.extend(t)

        return all_module_metrics
