import pandas as pd

"""
icmplib documentation https://pypi.org/project/icmplib/
ICMPSocketError covers timeout errors etc.
As long as the program is ran with root privilege and 
URIs are correct, this is all that is needed.
"""
from icmplib import ping, multiping, traceroute, Host, Hop, ICMPSocketError

from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime
from time import perf_counter

"""
When doing traceroute, check if the last hop ip is one of
ip(s) returned by gethostbyname_ex to make sure traceroute didn't timeout
"""
from socket import gethostbyname_ex

from util.logging_color import _info, _warn, _error, _debug
from util.heptatet import Heptate, HEPTATE_ENTRIES

# Required file to read from
POPULAR_SITES = 'popular_us_sites.csv'
SITES = 'sites.csv'

# directory where all the data files are saved
DATA_DIR_PATH = 'data'

# data on popular sites
POPULAR_SITES_DATA = 'popular_sites_data.csv'
# data on (frequently) visited sites
SITES_DATA = 'sites_data.csv'

"""
Heptatets (derivative, I know)
site (url): url of website
time: utc in iso format. `str(datetime.utcnow().isoformat())`
ip: ip address of site/url
hop_num: the hop from host, use `.distance` attribute when using icmplib. 0 if pinging
min_rtt: use `.min_rtt` attribute when using icmplib
avg_rtt: use `.avg_rtt` attribute when using icmplib
max_rtt: use `.max_rtt` attribute when using icmplib
"""
DATA_COLUMNS = HEPTATE_ENTRIES # ['site', 'time', 'ip', 'hop_num', 'min_rtt', 'avg_rtt', 'max_rtt']

def main():
    # parser = ArgumentParser()
    # subparser = parser.add_subparsers()
    
    # # Create parser for the "collect" sub-command
    # parser_collect = subparser.add_parser('collect')
    # parser_collect.add_argument('set', choices=['popular', 'sites'], required=True)
    # parser.parse_args()
    
    # ######################################################## #
    # ################### Setting Up Files ################### #
    # ######################################################## #
    # Check for required files
    popular_sites = Path(POPULAR_SITES)
    if not popular_sites.exists():
        print(_error(f'{POPULAR_SITES} does not exist and is needed'))
        exit(1)
    
    sites = Path(SITES)
    if not sites.exists():
        print(_error(f'{SITES} does not exist and is needed'))
        exit(1)
    
    # Setting up data files if doesn't exist
    data_dir = Path(DATA_DIR_PATH)
    if not data_dir.exists():
        data_dir.mkdir()
        print(_info(f'Created {DATA_DIR_PATH} directory'))

    popular_sites_data_file = data_dir.joinpath(POPULAR_SITES_DATA)
    if not popular_sites_data_file.exists():
        popular_sites_data_file.touch(exist_ok=False)
        print(_info(f'Created {popular_sites_data_file} file'))

    sites_data_file = data_dir.joinpath(SITES_DATA)
    if not sites_data_file.exists():
        sites_data_file.touch(exist_ok=False)
        print(_info(f'Created {sites_data_file} file'))

    # write in csv headers for empty file
    if popular_sites_data_file.stat().st_size == 0:
        pd.DataFrame(columns=DATA_COLUMNS).to_csv(popular_sites_data_file, index=False)
        
    # write in csv headers for empty file
    if sites_data_file.stat().st_size == 0:
        pd.DataFrame(columns=DATA_COLUMNS).to_csv(sites_data_file, index=False)

    # ######################################################## #
    # ##################### Read in files #################### #
    # ######################################################## #
    popular_sites_list: list[str] = list(pd.read_csv(popular_sites, squeeze=True))
    print(_debug(popular_sites_list))
    
    sites_list: list[str] = list(pd.read_csv(sites, squeeze=True))
    print(_debug(sites_list))
    
    popular_sites_data_df = pd.read_csv(popular_sites_data_file)
    
    sites_data_df = pd.read_csv(sites_data_file)
        
    # list of Heptatet from popular sites data
    popular_sites_data_list: list[Heptate] = list(popular_sites_data_df.itertuples(index=False, name='Heptatet'))
    
    # list of Heptatet from sites data
    sites_data_list: list[Heptate] = list(sites_data_df.itertuples(index=False, name='Heptatet'))
    print(_debug(sites_data_list))

    print('===========================')
    _collect_data(popular_sites_data_file, popular_sites_list)
    

def _collect_data(data_file: Path, sites_list: list[str]):
    print(_info(f'Start collecting on {sites_list}, save to {data_file}'))
    start = perf_counter()
    new_data = []
    for address in sites_list:
        print(_debug(address))
        new_data.extend(trace_url(address))
    pd.DataFrame(data=new_data).to_csv(data_file, index=False, mode='a', header=False)
    end = perf_counter()
    print(_info(f'Done in {end - start} seconds'))


def trace_url(address: str) -> list[Heptate]:
    _, _, possible_ips = gethostbyname_ex(address)
    hops: list[Hop] = traceroute(address)
    if hops[-1].address not in possible_ips:
        # last hop of traceroute not in DNS address record
        # traceroute might've timed out or DNS is out of date
        # regardless, something is wrong
        print(_warn(f'{address} ip mismatch: {hops[-1].address} not one of {possible_ips}'))
        return []
    return [Heptate(address,
                    __time_now(),
                    h.address,
                    h.distance,
                    h.min_rtt,
                    h.avg_rtt,
                    h.max_rtt) for h in hops]

def ping_url(address: str):
    _, _, possible_ips = gethostbyname_ex(address)
    host = ping(address)
    if host.address not in possible_ips:
        print(_warn(f'{address} ip mismatch: {host.address} not one of {possible_ips}'))
        return None
    return Heptate(address,
                   __time_now(),
                   host.address,
                   0,
                   host.min_rtt,
                   host.avg_rtt,
                   host.max_rtt)

def __time_now():
    return str(datetime.utcnow().isoformat())

if __name__ == '__main__':
    main()
    