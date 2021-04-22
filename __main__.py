from argparse import ArgumentParser
from pathlib import Path
from pprint import pformat
from socket import gaierror, gethostbyname_ex
from time import perf_counter

import numpy as np
import pandas as pd
from icmplib import Hop, Host, ping, traceroute

from util.heptatet import HEPTATE_ENTRIES, Heptate
from util.logging_color import _debug, _error, _info, _warn

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
    parser_collect.add_argument('set', choices=['popular', 'sites', 'all'])
    parser_collect.set_defaults(func=lambda args: _handle_collect(args,
                                                                  popular_sites_data_file,
                                                                  popular_sites_list,
                                                                  sites_data_file,
                                                                  sites_list))

    # Create parser for "analyze" sub-command
    parser_analyze = subparser.add_parser('analyze')
    # at least 1 site should be supplied for analysis
    parser_analyze.add_argument('site', nargs=1)
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
    custom_sites_data_df = pd.read_csv(sites_data_file,
                                       parse_dates=True,
                                       infer_datetime_format=True,
                                       index_col=DATA_COLUMNS[0])
    site = args.site[0]

    # Find last hops for each popular sites, which we use to compare max RTTs against
    popular_sites_data_df = extract_last_hops(popular_sites_data_df)

    print(_info('Checking popular hosts...'))
    any_success = False
    all_success = True
    for popular_site in popular_sites_list:
        site_df = popular_sites_data_df[popular_sites_data_df['site'] == popular_site]
        try:
            zscore, curr_max_rtt, mean_max_rtt = site_max_rtt_stats(popular_site,
                                                                    site_df)
        except gaierror:
            all_success = False

        if zscore < 3:
            any_success = True
            print(_info(f'{popular_site} appears normal'))
        else:
            all_success = False
            print(_error(f'{popular_site} appears problematic '
                         f'(max RTT: {curr_max_rtt}, '
                         f'avg. past max RTT: {mean_max_rtt})'))

    # If we’re experiencing problems with all popular hosts, we conclude that it's a
    # problem with our ISP.
    if not any_success:
        print()
        print(_error('All popular sites appear problematic, either having abnormally '
                     'high RTT or unreachable. This like indicates a gateway router or '
                     ' ISP problem.'))
        return

    # If we’re experiencing problems with some, but not all popular hosts, we conclude
    # that it’s a problem with intermediate AS(es), and we can run traceroute on our
    # host of interest to get a finer granularity of information.

    # First get all the hops between this device and the host of interest
    print()
    print(_info('Checking host of interest...'))
    hops = trace_url(site)
    culprit = None
    for hop in hops:
        # Skip this hop if we've never seen it before
        if hop.ip not in custom_sites_data_df['ip'].values:
            print(_warn(f'Hop #{hop.hop_num} ({hop.ip}) is not in historical data'))
            continue

        ip_df = custom_sites_data_df[custom_sites_data_df['ip'] == hop.ip]
        zscore, curr_max_rtt, mean_max_rtt = max_rtt_stats(hop, ip_df)
        if zscore < 3:
            print(_info(f'Hop #{hop.hop_num} ({hop.ip}) appears normal'))
        else:
            print(_error(f'Hop #{hop.hop_num} ({hop.ip}) appears problematic '
                         f'(max RTT: {curr_max_rtt}, '
                         f'avg. past max RTT: {mean_max_rtt}); '
                         'this could be the culprit.'))

            # Remember the first problematic hop
            if culprit is None:
                culprit = hop

    print()
    if culprit is not None:
        print(_error(f'Hop #{culprit.hop_num} ({culprit.ip}) on the path from this '
                     f'device to {site} was the first one that appeared problematic '
                     '(having an abnormally high RTT). This is likely the culprit of '
                     'your connection problem.'))
    else:
        print(_info('No connection problem detected. Everything seems to be working.'))


def _handle_traceroute(args, sites_data_file: Path):
    _collect_data(sites_data_file, args.site)


def _handle_collect(args, popular_sites_data_file: Path, popular_sites_list: list[str],
                    sites_data_file: Path, sites_list: list[str]):
    if args.set == 'popular':
        _collect_data(popular_sites_data_file, popular_sites_list)
    elif args.set == 'sites':
        _collect_data(sites_data_file, sites_list)
    else:  # 'all'
        _collect_data(popular_sites_data_file, popular_sites_list)
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


def trace_url(address: str, num_pings=NUM_PINGS) -> list[Heptate]:
    _, _, possible_ips = gethostbyname_ex(address)
    hops: list[Hop] = traceroute(address, count=num_pings)
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


def ping_url(address: str, num_pings=NUM_PINGS):
    _, _, possible_ips = gethostbyname_ex(address)
    host = ping(address, count=num_pings)
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


def multi_ping_urls(addresses: list[str], num_pings=NUM_PINGS):
    return [ping_url(address, num_pings) for address in addresses]


def __utc_time_now():
    return pd.to_datetime('now', utc=True)


def site_max_rtt_stats(url: str, past_df: pd.DataFrame) -> tuple[float, float, float]:
    ping_data = ping_url(url)
    return max_rtt_stats(ping_data, past_df)


# TODO: Make the return type a dataclass/namedtuple
def max_rtt_stats(current: Heptate, past_df: pd.DataFrame) -> tuple[float, float, float]:
    '''Returns (zscore, current_max_rtt, mean_max_rtt_without_outliers).'''
    max_rtt_col = past_df['max_rtt']

    # Remove outliers 3 STDs above the mean
    abs_zscores = np.abs((max_rtt_col - max_rtt_col.mean()) / max_rtt_col.std())
    max_rtt_col = max_rtt_col[abs_zscores < 3]

    mean_max_rtt = max_rtt_col.mean()
    zscore = (current.max_rtt - mean_max_rtt) / max_rtt_col.std()

    return zscore, current.max_rtt, mean_max_rtt


def extract_last_hops(df: pd.DataFrame) -> pd.DataFrame:
    last_hop_indices = []
    for i in range(len(df) - 1):
        if df.iloc[i]['site'] != df.iloc[i + 1]['site']:
            last_hop_indices.append(i)
    last_hop_indices.append(len(df) - 1)

    return df.iloc[last_hop_indices]


if __name__ == '__main__':
    main()
