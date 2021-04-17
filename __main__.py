import pandas as pd

# icmplib documentation https://pypi.org/project/icmplib/
from icmplib import ping, multiping, traceroute, resolve, Host, Hop

from argparse import ArgumentParser
from pathlib import Path
"""
When doing traceroute, check if the last hop ip is one of
ip(s) returned by gethostbyname_ex to make sure traceroute didn't timeout
"""
from socket import gethostbyname_ex
from util.logging_color import _info, _warn, _error, _debug

# Required file to read from
POPULAR_SITES = 'popular_us_sites.csv'
SITES = 'sites.csv'

# directory where all the data files are saved
DATA_DIR_PATH = 'data'

# data on popular sites
POPULAR_SITES_DATA = 'popular_sites_data.csv'
# data on (frequently) visited sites
SITES_DATA = 'sites_data.csv'

DATA_COLUMNS = ['site', 'ip', 'time', 'hop_num', 'min_rtt', 'avg_rtt', 'max_rtt']

def main():
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

    # ######################################################## #
    # ##################### Read in files #################### #
    # ######################################################## #
    popular_sites_list = list(pd.read_csv(popular_sites, squeeze=True))
    print(_debug(popular_sites_list))
    
    sites_list = list(pd.read_csv(sites, squeeze=True))
    print(_debug(sites_list))
    
    
    if popular_sites_data_file.stat().st_size == 0: # empty file
        popular_sites_data_df = pd.DataFrame(columns=DATA_COLUMNS)
    else:
        popular_sites_data_df = pd.read_csv(popular_sites_data_file)
    popular_sites_data_list = list(popular_sites_data_df.itertuples(index=False, name=None))
    print(_debug(popular_sites_data_list))
    
    
    if sites_data_file.stat().st_size == 0: # empty file
        sites_data_df = pd.DataFrame(columns=DATA_COLUMNS)
    else:
        sites_data_df = pd.read_csv(sites_data_file)
    sites_data_list = list(sites_data_df.itertuples(index=False, name=None))
    print(_debug(sites_data_list))

if __name__ == '__main__':
    main()
    