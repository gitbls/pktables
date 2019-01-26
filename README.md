# pktables - Port knocker iptables helper

pktables simplifies management of multiple knockd-managed services

## Overview

Linux `knockd` is a port-knock server that looks for specific network *knock* sequences of port-hits, and when one is observed,
executes a command. Typically the command executed opens a port via iptables, although there are no restrictions on what the command
actually does.

`pktables` is a Python script that simplifies management of iptables rules for port knocking. `pktables` implements commmands to:

* Initialize an iptables service chain for a particular port
* Remove a service chain from iptables
* Add a specific IP address to an iptables service chain
* Delete a specific IP address form an iptables service chain
* List current iptables rules (for convenience)

When pktables initializes an iptables service chain, it creates the following:

* A new iptables chain (pk-servicename) that is terminated with a DROP rule
* A rule at the end of the iptables INPUT chain that jumps to the newly-created iptables chain for packets meeting the specified criteria (port, protocol, etc).

Once established, any packets hitting the host on the target port and criteria are by default denied. The pktables add command adds new IPs in IP-sorted order to the pk-servicename chain with an ACCEPT target ahead of the DROP rule.

## Commands

The *servicename* in the pktables commands is a string of your choice. Typically, you'll use the protocol name (e.g., *ssh*), but you can name it whatever you'd like.

* `pktables init servicename --port portnum [--udp | --syn] [--accept]` - The *init* command creates the pk-servicename iptables chain and adds the rule to the INPUT chain that jumps to this new chain.

    * *servicename* is required specifies the service user-specified name for the service. All subsequent pktables commands for this service must use the same servicename.

    * `--port` is required and specifies TCP or UDP the port number for the service

    * `--udp` indicates that the service is for UDP (default is TCP). `--syn` specifies that only initial TCP connections should be managed by iptables. `--udp` and `--syn` are mutually exclusive and optional except as needed.

    * `--accept` terminates the pk-servicename chain with an ACCEPT rather than DROP, which you might want to do for monitoring or early testing. `--accept` is optional.

* `pktables remove servicename` - Removes the pk-servicename chain and the jump to it in the INPUT chain

* `pktables add ipaddr --service servicename` - Adds an entry to the pk-servicename chain to ACCEPT packets from the specified IP address. `--service servicename` is required.

* `pktables delete ipaddr --service servicename` - Removes the entry for the specified IP address from the pk-servicename chain. `--service servicename` is required.

## Usage

Typically you'll do the pktables init commands at system startup, and after iptables has been initialized. New services can also be initialized during normal system operation, but make sure you add them to system startup somewhere for the next system restart!

Example knockd.conf entry

```
# Initialization: pktables init ssh --port 22 --syn
[opencloseSSH]
        sequence      = 11111, 22222
        seq_timeout   = 10
        tcpflags      = syn
        start_command = /usr/local/bin/pktables add %IP% --service ssh
        cmd_timeout   = 30
        stop_command  = /usr/local/bin/pktables delete %IP% --service ssh
```

This example assumes that the pk-ssh table with a DROP rule at the end was created per the comment. When a valid knock is received, the start_command will add the IP address to the pk-ssh chain. 30 seconds later it will remove that IP address from the chain. Since a valid connection starts with a TCP SYN packet, only SYN packets need to be filtered.

