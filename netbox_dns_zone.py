#!/usr/bin/env python3

import argparse
import re

import pynetbox
from netaddr import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', '-p', help='Prefix, in the format of 192.168.178.0/24')
    parser.add_argument('--output', '-o', help='Path to output zone file.')
    parser.add_argument('--config', '-c', help='Path to configuration file.')
    parser.add_argument('--token', '-t', required=True)
    parser.add_argument('--uri', '-u', required=True)
    args = parser.parse_args()

    nb = pynetbox.api(url=args.uri, token=args.token)

    # XXX: get the subnet mask from args.prefix
    subnet_mask = 24
    prefix = nb.ipam.prefixes.get(q='192.168.178.0', mask_length=subnet_mask)
    #print(f'{prefix}: {prefix.serialize()}')

    # Derive the serial from the last_updated timestamp of the prefix.
    # This is a stable identifier, but it does mean the serial can get
    # incremented for changes unrelated to dns_name.
    serial = re.sub(r'^(\d+)-(\d+)-(\d+)T\d+:\d+:(\d+).*', r'\1\2\3\4', prefix.last_updated)
    nameserver = prefix.custom_fields['nameserver']
    zone = prefix.custom_fields['dns_zone']

    header = (
        f'; {prefix.description}\n'
        f'$TTL 1800\n'
        f'$ORIGIN {zone}.\n'
    )

    soa = (
        f'{"@    1H":<20}{"IN":<10}{"SOA":<10} {nameserver} hostmaster.{zone}. (\n'
        f'{serial:>40} ; serial\n'
        f'{"1H":>40} ; refresh\n'
        f'{"15":>40} ; retry\n'
        f'{"1W":>40} ; expire\n'
        f'{"1H":>40} ; minimum ttl\n'
	f')\n'
    )

    print(header)
    print(soa)
    print(f'{" " * 20}{"IN":<10}{"NS":<10}{nameserver:<20}')

    # Now get all the IPs netbox knows of within that prefix
    ips = nb.ipam.ip_addresses.filter(q='192.168.178.')
    for ip in ips:
        ip_str = re.sub(r'\/.*$', '', str(ip))
        host = ip.dns_name.replace(f'.{zone}', '')
        cnames = ip.custom_fields.get('dns_cname')
        if not host:
            continue

        print(f'{host:<20}{"IN":<10}{"A":<10}{ip_str:<20}')

        # Custom fields are set to None by default.
        if cnames:
            [print(f'{cname:<20}{"IN":<10}{"CNAME":<10}{ip_str:<20}') for cname in cnames.split(',')]


if __name__ == '__main__':
    main()
