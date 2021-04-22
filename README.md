# ClameIt

Client-side BlameIt Tool

## Table of Content

- [ClameIt](#clameit)
  - [Table of Content](#table-of-content)
  - [Software Requirement](#software-requirement)
  - [Set Up](#set-up)
  - [Run Program](#run-program)
    - [Collect Data](#collect-data)
    - [Analyze Sites](#analyze-sites)
    - [Traceroute Sites](#traceroute-sites)
  - [Run Cron Job](#run-cron-job)
    - [1. Give cron full disk access](#1-give-cron-full-disk-access)
    - [2. Find absolute path for python3](#2-find-absolute-path-for-python3)
    - [3. Create cron job](#3-create-cron-job)
    - [4. Delete cron job](#4-delete-cron-job)
  - [Resources](#resources)
  - [Caveat](#caveat)

## Software Requirement

- OS: MacOS strongly preferred
- Python: 3.9.0+

## Set Up

```bash
% git clone https://github.com/bojinyao/ClameIt.git
% cd ClameIt
% pip3 install -r requirements.txt
```

## Run Program

For help:

`python3 ClameIt -h`

The ICMP package used in this project requires the code run with _root_ privilege

### Collect Data

To collect data for popular sites that serve as baseline: `sudo python3 ClameIt collect popular`

To collect data for frequent sites: `sudo python3 ClameIt collect sites`

### Analyze Sites

To analyze urls: `sudo python3 ClameIt analyze website1 [website2...]`

### Traceroute Sites

To run traceroute on sites not defined in 'sites_data.csv': `sudo python3 ClameIt traceroute website1 [website2...]`

## Run Cron Job

Note: this section assumes MacOS, it might work for Linux, but definitely NOT for Windows

### 1. Give cron full disk access

Checkout [Caveat](#caveat) below

### 2. Find absolute path for python3

```bash
% which python3
/usr/local/bin/python3 # Example output
```

### 3. Create cron job

```bash
sudo crontab -e
```

After entering password, this will open up default text editor on your computer. Add the following and replace information in `[...]`:

```bash
0,20,40 6-23,0,1,2 * * * [absolute path to python3] [absolute path to ClameIt]ClameIt/__main__.py collect all > /tmp/script.py.log 2>&1
```

NOTE: you must use _absolute paths_ to `python3`, as well as the `__main__.py` file to make sure cron will work correctly as super user!

The above cron job will run `collect all` command nearly 24 hours (except between 3 and 5 clock in the morning) at 0th, 20th, and 40th minutes until the job is deleted. Errors and standard outputs are directed to `/tmp/script.py.log`, to edit or delete this file, use sudo, like `sudo vim /tmp/script.py.log` or `sudo rm -f /tmp/script.py.log`. Basically it will run 3 times per hour, 21 hours a day.

To update the cron schedule, checkout <https://crontab.guru/>

You can checkout a list of cron jobs running as `root` with:

```bash
sudo crontab -l
```

### 4. Delete cron job

Open `crontab`:

```bash
sudo crontab -e
```

and delete the job, then save, cron will update automatically.

## Resources

1. Configure cron-job scheduling: <https://crontab.guru/>
2. Cron job logging: <https://unix.stackexchange.com/questions/24640/running-python-script-via-cron-with-sudo>

## Caveat

For recent MacOS releases, it is recommended to give `cron` Full Disk Access on Mac.

Tutorial: <https://blog.bejarano.io/fixing-cron-jobs-in-mojave>

Follow the section "Granting Full Disk Access to cron" in the above tutorial
