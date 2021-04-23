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

# ---------------------------- User Configurations --------------------------- #

# Required file to read from
POPULAR_SITES = 'popular_us_sites.csv'
FREQUENT_SITES = 'frequent_sites.csv'

# directory where all the data files are saved
DATA_DIR = 'data'

# -------------------------- Internal Configurations ------------------------- #

# data on popular sites
POPULAR_SITES_DATA = 'popular_sites_data.csv'
# data on (frequently) visited sites
FREQUENT_SITES_DATA = 'frequent_sites_data.csv'

BAD_POPULAR_SITES_DATA = f'bad_{POPULAR_SITES_DATA}'
BAD_FREQUENT_SITES_DATA = f'bad_{FREQUENT_SITES_DATA}'

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

    frequent_sites = target_dir.joinpath(FREQUENT_SITES)
    if not frequent_sites.exists():
        print(_error(f'{FREQUENT_SITES} does not exist and is needed'))
        exit(1)

    # ----------------- Setting Up Data Files ---------------- #
    # Create data directory
    data_dir = target_dir.joinpath(DATA_DIR)
    if not data_dir.exists():
        data_dir.mkdir()
        print(_info(f'Created {DATA_DIR} directory'))

    # Set up popular sites data file if necessary
    popular_sites_data_file = data_dir.joinpath(POPULAR_SITES_DATA)
    if not popular_sites_data_file.exists():
        popular_sites_data_file.touch(exist_ok=False)
        print(_info(f'Created {popular_sites_data_file} file'))

    if popular_sites_data_file.stat().st_size == 0:
        pd.DataFrame(columns=DATA_COLUMNS).to_csv(
            popular_sites_data_file, index=False)

    # Set up bad popular sites data file if necessary
    bad_popular_sites_data_file = data_dir.joinpath(BAD_POPULAR_SITES_DATA)
    if not bad_popular_sites_data_file.exists():
        bad_popular_sites_data_file.touch(exist_ok=False)
        print(_info(f'Created {bad_popular_sites_data_file} file'))
        
    if bad_popular_sites_data_file.stat().st_size == 0:
        pd.DataFrame(columns=DATA_COLUMNS).to_csv(
            bad_popular_sites_data_file, index=False)

    # Set up frequent sites data file if necessary
    frequent_sites_data_file = data_dir.joinpath(FREQUENT_SITES_DATA)
    if not frequent_sites_data_file.exists():
        frequent_sites_data_file.touch(exist_ok=False)
        print(_info(f'Created {frequent_sites_data_file} file'))

    if frequent_sites_data_file.stat().st_size == 0:
        pd.DataFrame(columns=DATA_COLUMNS).to_csv(frequent_sites_data_file, index=False)

    # Set up bad frequent sites data file if necessary
    bad_frequent_sites_data_file = data_dir.joinpath(BAD_FREQUENT_SITES_DATA)
    if not bad_frequent_sites_data_file.exists():
        bad_frequent_sites_data_file.touch(exist_ok=False)
        print(_info(f'Created {bad_frequent_sites_data_file} file'))
    
    if bad_frequent_sites_data_file.stat().st_size == 0:
        pd.DataFrame(columns=DATA_COLUMNS).to_csv(bad_frequent_sites_data_file, index=False)

    # ######################################################## #
    # ##################### Read in files #################### #
    # ######################################################## #
    popular_sites_list: list[str] = list(
        pd.read_csv(popular_sites, squeeze=True))

    frequent_sites_list: list[str] = list(pd.read_csv(frequent_sites, squeeze=True))

    # ######################################################## #
    # #################### Parse Arguments ################### #
    # ######################################################## #
    parser = ArgumentParser()
    subparser = parser.add_subparsers()

    # Create parser for "traceroute" sub-command
    parser_traceroute = subparser.add_parser('traceroute')
    parser_traceroute.add_argument('site', nargs='+')
    parser_traceroute.set_defaults(func=lambda args: _handle_traceroute(args,
                                                                        frequent_sites_data_file,
                                                                        bad_frequent_sites_data_file))

    # Create parser for the "collect" sub-command
    parser_collect = subparser.add_parser('collect')
    parser_collect.add_argument('set', choices=['popular', 'frequent', 'all'])
    parser_collect.set_defaults(func=lambda args: _handle_collect(args,
                                                                  popular_sites_data_file,
                                                                  bad_popular_sites_data_file,
                                                                  popular_sites_list,
                                                                  frequent_sites_data_file,
                                                                  bad_frequent_sites_data_file,
                                                                  frequent_sites_list))

    # Create parser for "analyze" sub-command
    parser_analyze = subparser.add_parser('analyze')
    # at least 1 site should be supplied for analysis
    parser_analyze.add_argument('site', nargs=1)
    parser_analyze.set_defaults(func=lambda args: _handle_analyze(args,
                                                                  popular_sites_data_file,
                                                                  popular_sites_list,
                                                                  frequent_sites_data_file,
                                                                  frequent_sites_list))

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
    ok, hops = trace_url(site)
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


def _handle_traceroute(args, sites_data_file: Path, sites_bad_data_file: Path):
    _collect_data(sites_data_file, sites_bad_data_file, args.site)


def _handle_collect(args, popular_sites_data_file: Path, bad_popular_sites_data_file: Path,
                    popular_sites_list: list[str],
                    frequent_sites_data_file: Path, bad_frequent_sites_data_file: Path,
                    frequent_sites_list: list[str]):
    if args.set == 'popular':
        _collect_data(popular_sites_data_file,
                      bad_popular_sites_data_file, popular_sites_list)
    elif args.set == 'frequent':
        _collect_data(frequent_sites_data_file,
                      bad_frequent_sites_data_file, frequent_sites_list)
    else:  # 'all'
        _collect_data(popular_sites_data_file,
                      bad_popular_sites_data_file, popular_sites_list)
        _collect_data(frequent_sites_data_file,
                      bad_frequent_sites_data_file, frequent_sites_list)


def _collect_data(data_file: Path, bad_data_file: Path, sites_list: list[str]):
    print(
        _info(f'Start collecting on:\n'
              f'{pformat(sites_list)}'))
    start = perf_counter()
    new_good_data = []
    new_bad_data = []
    for address in sites_list:
        print(_debug(address), end=' ', flush=True)
        s = perf_counter()
        ok, hops = trace_url(address)
        if ok:
            new_good_data.extend(hops)
        else:
            new_bad_data.extend(hops)
        e = perf_counter()
        print(_debug(f'{round(e - s, 2)} seconds'))
    if len(new_good_data) > 0:
        pd.DataFrame(data=new_good_data).to_csv(
            data_file, index=False, mode='a', header=False)
    if len(new_bad_data) > 0:
        pd.DataFrame(data=new_bad_data).to_csv(
            bad_data_file, index=False, mode='a', header=False)
    end = perf_counter()
    print(_info(f'Done in {round(end - start, 2)} seconds.\n'
                f'+ {len(new_good_data)} to {data_file}\n'
                f'+ {len(new_bad_data)} to {bad_data_file}'))


# ---------------------------------------------------------------------------- #
# ----------------------------- Helper Functions ----------------------------- #
# ---------------------------------------------------------------------------- #

"""
When doing traceroute or ping, check if the last hop ip is one of
ip(s) returned by gethostbyname_ex to make sure traceroute didn't timeout
and ping is pinging the right ip
"""


def trace_url(address: str, num_pings=NUM_PINGS):
    _, _, possible_ips = gethostbyname_ex(address)
    hops: list[Hop] = traceroute(address, count=num_pings)
    ok = True
    if hops[-1].address not in possible_ips:
        # last hop of traceroute not in DNS address record
        # traceroute might've timed out or DNS is out of date
        # regardless, something is wrong
        print(
            _warn(f'{address} ip mismatch: {hops[-1].address} not one of {possible_ips}'))
        ok = False
    return ok, [Heptate(__utc_time_now(),
                    address,
                    h.address,
                    h.distance,
                    h.min_rtt,
                    h.avg_rtt,
                    h.max_rtt) for h in hops]


def ping_url(address: str, num_pings=NUM_PINGS):
    t = __utc_time_now()
    host = ping(address, count=num_pings)
    alive = True
    if not host.is_alive:
        # Failed to reach address
        print(
            _warn(f'{address} not reachable'))
        alive = False
    return alive, Heptate(t,
                   address,
                   host.address,
                   0,
                   host.min_rtt,
                   host.avg_rtt,
                   host.max_rtt)

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
