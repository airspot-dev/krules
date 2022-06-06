from configurations import rulesdata as cfgp_rulesdata
from serviceconfigurations import rulesdata as scfgp_rulesdata
from featureconfigurations import rulesdata as fcfgp_rulesdata
from namespace import rulesdata as ns_rulesdata

# from krules_core.providers import proc_events_rx_factory
# from pprint import pprint
# proc_events_rx_factory().subscribe(
#     on_next=pprint
# )

rulesdata = cfgp_rulesdata + scfgp_rulesdata + fcfgp_rulesdata + ns_rulesdata

