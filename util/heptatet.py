from collections import namedtuple

"""
Heptatets (derivative, I know)
time (pandas datetime): pandas datetime object
site/url (str): url of website
ip (str): ip address of site/url
hop_num (int): the hop from host, use `.distance` attribute when using icmplib. 0 if pinging
min_rtt (float): use `.min_rtt` attribute when using icmplib
avg_rtt (float): use `.avg_rtt` attribute when using icmplib
max_rtt (float): use `.max_rtt` attribute when using icmplib
"""
HEPTATE_ENTRIES = ['time', 'site', 'ip', 'hop_num', 'min_rtt', 'avg_rtt', 'max_rtt']

Heptate = namedtuple('Heptatet', HEPTATE_ENTRIES)
