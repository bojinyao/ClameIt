import pandas as pd

# icmplib documentation https://pypi.org/project/icmplib/
from icmplib import ping, multiping, traceroute, resolve, Host, Hop

from argparse import ArgumentParser
from pathlib import Path
from util.logging import print_info, print_warning, print_error

# Required file to read from
POPULAR_SITES = 'popular_us_sites.csv'

# directory where all the data files are saved
DATA_DIR_PATH = 'data'

# data on popular sites
POPULAR_SITES_DATA = 'popular_sites_data.csv'
# data on (frequently) visited sites
SITES_DATA = 'sites_data.csv'


def main():
    popular_sites = Path(POPULAR_SITES)
    if not popular_sites.exists():
        print_error(f'{POPULAR_SITES} does not exist and is needed')
        exit(1)
    
    # Setting up data files if doesn't exist
    data_dir = Path(DATA_DIR_PATH)
    if not data_dir.exists():
        data_dir.mkdir()
        print_info(f'Created {DATA_DIR_PATH} directory')

    popular_sites_data_file = data_dir.joinpath(POPULAR_SITES_DATA)
    if not popular_sites_data_file.exists():
        popular_sites_data_file.touch(exist_ok=False)
        print_info(f'Created {popular_sites_data_file} file')

    sites_data_file = data_dir.joinpath(SITES_DATA)
    if not sites_data_file.exists():
        sites_data_file.touch(exist_ok=False)
        print_info(f'Created {sites_data_file} file')

    # read list of popular sites
    popular_sites_series = pd.read_csv(popular_sites, squeeze=True)
    print(popular_sites_series)


if __name__ == '__main__':
    main()
    