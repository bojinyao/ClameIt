"""
icmplib documentation https://pypi.org/project/icmplib/
ICMPSocketError covers timeout errors etc.
As long as the program is ran with root privilege and 
URIs are correct, this is all that is needed.
"""

from time import perf_counter
from datetime import datetime
from pathlib import Path
from argparse import ArgumentParser
from icmplib import ping, multiping, traceroute, Host, Hop, ICMPSocketError
from pprint import pformat
from util.heptatet import Heptate, HEPTATE_ENTRIES
from util.logging_color import _info, _warn, _error, _debug

from socket import gethostbyname_ex
import pandas as pd


# Required file to read from
POPULAR_SITES = 'popular_us_sites.csv'
SITES = 'sites.csv'

# directory where all the data files are saved
DATA_DIR = 'data'

# data on popular sites
POPULAR_SITES_DATA = 'popular_sites_data.csv'
# data on (frequently) visited sites
SITES_DATA = 'sites_data.csv'

# Perform 5 pings per traceroute/ping for data collection
NUM_PINGS = 5

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
DATA_COLUMNS = HEPTATE_ENTRIES  # ['time', 'site', 'ip', 'hop_num', 'min_rtt', 'avg_rtt', 'max_rtt']


def main():
    # ######################################################## #
    # ################### Setting Up Files ################### #
    # ######################################################## #
    # NOTE: All I/O is relative to the directory where *this* file is
    target_dir = Path(__file__).parent
    # Check for required files
    popular_sites = target_dir.joinpath(POPULAR_SITES)
    if not popular_sites.exists():
        print(_error(f'{POPULAR_SITES} does not exist and is needed'))
        exit(1)

    sites = target_dir.joinpath(SITES)
    if not sites.exists():
        print(_error(f'{SITES} does not exist and is needed'))
        exit(1)

    # Setting up data files if doesn't exist
    data_dir = target_dir.joinpath(DATA_DIR)
    if not data_dir.exists():
        data_dir.mkdir()
        print(_info(f'Created {DATA_DIR} directory'))

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
        pd.DataFrame(columns=DATA_COLUMNS).to_csv(
            popular_sites_data_file, index=False)

    # write in csv headers for empty file
    if sites_data_file.stat().st_size == 0:
        pd.DataFrame(columns=DATA_COLUMNS).to_csv(sites_data_file, index=False)

    # ######################################################## #
    # ##################### Read in files #################### #
    # ######################################################## #
    popular_sites_list: list[str] = list(
        pd.read_csv(popular_sites, squeeze=True))

    sites_list: list[str] = list(pd.read_csv(sites, squeeze=True))

    # ######################################################## #
    # #################### Parse Arguments ################### #
    # ######################################################## #
    parser = ArgumentParser()
    subparser = parser.add_subparsers()

    # Create parser for "traceroute" sub-command
    parser_traceroute = subparser.add_parser('traceroute')
    parser_traceroute.add_argument('site', nargs='+')
    parser_traceroute.set_defaults(func=lambda args: _handle_traceroute(args,
                                                                        sites_data_file))

    # Create parser for the "collect" sub-command
    parser_collect = subparser.add_parser('collect')
    parser_collect.add_argument('set', choices=['popular', 'sites'])
    parser_collect.set_defaults(func=lambda args: _handle_collect(args,
                                                                  popular_sites_data_file,
                                                                  popular_sites_list,
                                                                  sites_data_file,
                                                                  sites_list))

    # Create parser for "analyze" sub-command
    parser_analyze = subparser.add_parser('analyze')
    # at least 1 site should be supplied for analysis
    parser_analyze.add_argument('site', nargs='+')
    parser_analyze.set_defaults(func=lambda args: _handle_analyze(args,
                                                                  popular_sites_data_file,
                                                                  popular_sites_list,
                                                                  sites_data_file,
                                                                  sites_list))

    args = parser.parse_args()
    args.func(args)

# ---------------------------------------------------------------------------- #
# --------------------------- Sub-command Handlers --------------------------- #
# ---------------------------------------------------------------------------- #


def _handle_analyze(args, popular_sites_data_file: Path, popular_sites_list: list[str],
                    sites_data_file: Path, sites_list: list[str]):
    popular_sites_data_df = pd.read_csv(popular_sites_data_file, 
                                        parse_dates=True, 
                                        infer_datetime_format=True,
                                        index_col=DATA_COLUMNS[0])

    sites_data_df = pd.read_csv(sites_data_file, 
                                parse_dates=True, 
                                infer_datetime_format=True,
                                index_col=DATA_COLUMNS[0])
    
    print(_debug(f'{args.site}'))
    # TODO: analysis logic
    print(popular_sites_data_df)
    print(sites_data_df)


def _handle_traceroute(args, sites_data_file: Path):
    _collect_data(sites_data_file, args.site)


def _handle_collect(args, popular_sites_data_file: Path, popular_sites_list: list[str],
                    sites_data_file: Path, sites_list: list[str]):
    if args.set == 'popular':
        _collect_data(popular_sites_data_file, popular_sites_list)
    else:  # 'sites'
        _collect_data(sites_data_file, sites_list)


def _collect_data(data_file: Path, sites_list: list[str]):
    print(
        _info(f'Start collecting on {pformat(sites_list)}, save to {data_file}'))
    start = perf_counter()
    new_data = []
    for address in sites_list:
        print(_debug(address), end=' ', flush=True)
        s = perf_counter()
        new_data.extend(trace_url(address))
        e = perf_counter()
        print(_debug(f'{round(e - s, 2)} seconds'))
    pd.DataFrame(data=new_data).to_csv(
        data_file, index=False, mode='a', header=False)
    end = perf_counter()
    print(_info(f'Done in {round(end - start, 2)} seconds'))


# ---------------------------------------------------------------------------- #
# ----------------------------- Helper Functions ----------------------------- #
# ---------------------------------------------------------------------------- #

"""
When doing traceroute or ping, check if the last hop ip is one of
ip(s) returned by gethostbyname_ex to make sure traceroute didn't timeout
and ping is pinging the right ip
"""


def trace_url(address: str) -> list[Heptate]:
    _, _, possible_ips = gethostbyname_ex(address)
    hops: list[Hop] = traceroute(address, count=NUM_PINGS)
    if hops[-1].address not in possible_ips:
        # last hop of traceroute not in DNS address record
        # traceroute might've timed out or DNS is out of date
        # regardless, something is wrong
        print(
            _warn(f'{address} ip mismatch: {hops[-1].address} not one of {possible_ips}'))
        return []
    return [Heptate(__utc_time_now(),
                    address,
                    h.address,
                    h.distance,
                    h.min_rtt,
                    h.avg_rtt,
                    h.max_rtt) for h in hops]


def ping_url(address: str):
    _, _, possible_ips = gethostbyname_ex(address)
    host = ping(address, count=NUM_PINGS)
    if host.address not in possible_ips:
        # last hop of traceroute not in DNS address record
        # traceroute might've timed out or DNS is out of date
        # regardless, something is wrong
        print(
            _warn(f'{address} ip mismatch: {host.address} not one of {possible_ips}'))
        return None
    return Heptate(__utc_time_now(),
                   address,
                   host.address,
                   0,
                   host.min_rtt,
                   host.avg_rtt,
                   host.max_rtt)


def __utc_time_now():
    return pd.to_datetime('now', utc=True)


if __name__ == '__main__':
    main()
