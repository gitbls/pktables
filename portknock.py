#!/usr/bin/env python3
#
# Lightly updated version originally from: https://github.com/grongor/knock
#
import argparse
import select
import socket
import sys
import time


class Knocker(object):
    def __init__(self, args: list):
        self._parse_args(args)

    def _parse_args(self, args: list):
        parser = argparse.ArgumentParser(\
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter,\
                                         description='Port knock client forked from https://github.com/grongor/knock')

        parser.add_argument('-t', '--timeout', type=int, default=200,
                            help='Milliseconds to wait on hanging connection')
        parser.add_argument('-d', '--delay', type=int, default=200,
                            help='Milliseconds to wait between each knock')
        parser.add_argument('-u', '--udp', help='Use UDP instead of TCP by default', action='store_true')
        parser.add_argument('-v', '--verbose', help='Be verbose', action='store_true')
        parser.add_argument('host', help='Hostname or IP address of target host')
        parser.add_argument('ports', metavar='port[:protocol]', nargs='+',
                            help='Port(s) to knock; protocol [tcp, udp] is optional')

        args = parser.parse_args(args)
        self.timeout = args.timeout / 1000
        self.delay = args.delay / 1000
        self.default_udp = args.udp
        self.ports = args.ports
        self.verbose = args.verbose

        try:
            self.address_family, _, _, _, ip = socket.getaddrinfo(
                host=args.host,
                port=None,
                flags=socket.AI_ADDRCONFIG
            )[0]
            self.ip_address = ip[0]
        except socket.gaierror as err:
            print(f"? Socket error; Is '{args.host}' a known host")
            raise SystemExit(err)

    def knock(self):
        last_index = len(self.ports) - 1
        for i, port in enumerate(self.ports):
            use_udp = self.default_udp
            if port.find(':') != -1:
                port, protocol = port.split(':', 2)
                if protocol.lower() == 'tcp':
                    use_udp = False
                elif protocol.lower() == 'udp':
                    use_udp = True
                else:
                    error = 'Invalid protocol "{}"; Allowed values are: "tcp" and "udp"'
                    raise ValueError(error.format(protocol))

            if self.verbose:
                print(f'Knock {"udp" if use_udp else "tcp"} {port} {self.ip_address} {port}')

            s = socket.socket(self.address_family, socket.SOCK_DGRAM if use_udp else socket.SOCK_STREAM)
            s.setblocking(False)

            socket_address = (self.ip_address, int(port))
            if use_udp:
                s.sendto(b'', socket_address)
            else:
                s.connect_ex(socket_address)
                select.select([s], [s], [s], self.timeout)

            s.close()

            if self.delay and i != last_index:
                time.sleep(self.delay)


if __name__ == '__main__':
    Knocker(sys.argv[1:]).knock()
