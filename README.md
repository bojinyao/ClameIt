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

## Software Requirement

- OS: MacOS preferred
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
