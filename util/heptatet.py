from collections import namedtuple

"""
Heptatets (derivative, I know)
site (url): url of website
ip: ip address of site/url
time: utc in iso format. `str(datetime.utcnow().isoformat())`
hop_num: the hop from host, use `.distance` attribute when using icmplib. 0 if pinging
min_rtt: use `.min_rtt` attribute when using icmplib
avg_rtt: use `.avg_rtt` attribute when using icmplib
max_rtt: use `.max_rtt` attribute when using icmplib
"""
HEPTATE_ENTRIES = ['site', 'ip', 'time', 'hop_num', 'min_rtt', 'avg_rtt', 'max_rtt']

Heptate = namedtuple('Heptatet', HEPTATE_ENTRIES)
