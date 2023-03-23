# pktables - Simplified port knocking with knockd

pktables simplifies management of knockd-managed services

## Overview

Linux `knockd` is a <a href="https://en.wikipedia.org/wiki/Port_knocking">port-knock</a> server that looks for specific network *knock* sequences of port-hits. When a known knock sequence is observed,
knockd executes a pre-defined command or set of commands.

Typically the executed command opens a port via iptables, although there are no restrictions on what the command
actually does.

`pktables` is a Python script that simplifies management of iptables rules for port knocking. `pktables` removes the need for you to deal with arcane `iptables` commands. `pktables` implements commmands to:

* Initialize or remove an iptables service chain for a particular port
* Add a specific IP address to an iptables service chain, which enables that IP address to access the port
* Delete a specific IP address form an iptables service chain, which disables that IP address from further port access

When pktables initializes an iptables service chain, it creates the following:

* A new iptables chain, `pk-servicename` (you specify the servicename), that is terminated with a DROP rule. Any connection attempts that are not enabled by a prior rule in the chain will fail.
* A rule in the iptables INPUT chain that jumps to the newly-created iptables chain for packets meeting the specified criteria (port, protocol, etc).

Once established, any packets hitting the host on the target port and criteria are by default denied. The `pktables add` command adds new IPs in IP-sorted order to the pk-servicename chain with an ACCEPT target ahead of the chain-ending DROP rule.

## Installation

The simplest way to install `knockd` and `pktables` is to use the Installer:
```
curl -L https://raw.githubusercontent.com/gitbls/pktables/master/Install-pktables | bash
```

If you prefer to install it manually:

```
sudo apt update
sudo apt install knockd iptables
sudo curl -L https://raw.githubusercontent.com/gitbls/pktables/master/pktables -o /usr/local/bin/pktables
sudo curl -L https://raw.githubusercontent.com/gitbls/pktables/master/knockd-helper -o /usr/local/bin/knockd-helper
sudo curl -L https://raw.githubusercontent.com/gitbls/pktables/master/knockd.service -o /etc/systemd/system/knockd.service
```

Then, for either install method:
* `sudoedit /etc/knockd.conf` to configure your port knocking (See below for details)
* `sudoedit /usr/local/bin/knockd-helper` to configure the port knock table initialization, which is run at system startup
* Once everything is working correctly:
    * `sudo systemctl enable knockd`
    * `sudoedit /etc/default/knockd.conf` and change START_KNOCKD=0 to START_KNOCKD=1. This will enable knockd to start automatically at system boot.
* Reboot for one last end-to-end test and check the system logs: `sudo journalctl -b`

## Usage

The `pktables init` commands will be run at system startup after iptables has been initialized. New services can also be initialized during normal system operation, but make sure you add them to /usr/local/bin/knockd-helper so that knocking works after a system restart.

Example knockd.conf entry for SSH

```
# Initialization: pktables init ssh --port 22 --syn
[opencloseSSH]
        sequence      = 11111, 22222
        seq_timeout   = 10
        tcpflags      = syn
        start_command = pktables add %IP% --service ssh
        cmd_timeout   = 30
        stop_command  = pktables delete %IP% --service ssh
```

This example assumes that the `pktables init` command shown in the comment has been added to /usr/local/bin/knockd-helper.

When a valid knock is received, the start_command will add the IP address to the `pk-ssh` chain. 30 seconds later it will remove that IP address from the chain.

Since SSH connections start with a TCP SYN packet, only SYN packets need to be filtered. Other ssh packets will be summarily dropped if they are not related to an existing connection.

## pktables Commands

The *servicename* in the pktables commands is a string of your choice. Typically, you'll use the protocol name (e.g., *ssh*), but you can name it whatever you'd like.

* `pktables init servicename --port portnum [--udp | --syn] [--accept]` &mdash; The *init* command creates the pk-servicename iptables chain and adds the rule to the INPUT chain that jumps to this new chain. See the section <a href="README.md#handling-the-pktables-init-commands">Handling the pktables init commands</a> below for implementing seamless `pktables init`.

    * *servicename* is required specifies the service user-specified name for the service. All subsequent pktables commands for this service must use the same *servicename*.

    * `--port` is required and specifies TCP or UDP the port number for the service

    * `--udp` indicates that the service is for UDP (default is TCP). `--syn` specifies that only initial TCP connections should be managed by iptables. `--udp` and `--syn` are mutually exclusive and optional except as needed.

    * `--accept` terminates the pk-servicename chain with an ACCEPT rather than DROP, which you might want to do for monitoring or early testing. `--accept` is optional.

    * `--log` logs packets sent to this port that are not accepted

    * `--log-prefix` specifies the prefix string to use on the iptables log entry

    * `--log-burst` specifies the number of packets logged in a burst

    * `--log-level` specifies the level for the log entry

    * `--log-limit` specifies the maximum packets to log per /second, /minute, /hour, or /day, as in 10/second

* `pktables remove servicename` &mdash; Removes the pk-servicename chain and the jump to it from the INPUT chain

* `pktables add ipaddr --service servicename` &mdash; Adds an entry to the pk-servicename chain to ACCEPT packets from the specified IP address. `--service servicename` is required.

  You should rarely if ever need to use `pktables add` manually. It is primarily used automatically by knockd.

* `pktables delete ipaddr --service servicename` &mdash; Removes the entry for the specified IP address from the pk-servicename chain. `--service servicename` is required.

  You should rarely if ever need to use `pktables delete` manually. It is primarily used automatically by knockd.

## Handling the pktables init Commands

### Updating knockd.service

The most effective way to use `pktables init` is to have it be part of the knockd service startup.

For your convenience, a fully updated knockd.service is included is available on this GitHub. To use it, copy it to /etc/systemd/system (using sudo). `Install-pktables` does this for you.

### Adding required pktables init commands to knockd-helper

sudo copy knockd-helper from this GitHub to /usr/local/bin on your system. `Install-pktables` does this for you. It is a skeleton into which you can add your `pktables init` commands. Once this file is in place, the knockd.service will run it at system boot.

### Manually updating knockd.service from the Distro-provided version

`Install-pktables` provides a fully-updated knockd.service. You'll only need to do these steps if you enjoy editing Linux config files instead of using Install-pktables.

The distributed knockd.service has two issues:
* It does not wait on network-online.target, resulting in a knockd service failure since the system may start knockd before the network is online
* It does not provide an integrated mechanism for adding and removing iptables tables

The knockd.service here addresses both of these issues. If you don't use the provided knockd.service you need to edit it yourself:

* `sudo cp /lib/systemd/system/knockd.service /etc/systemd/system`
* `sudoedit /etc/systemd/system/knockd.service`
  * Add the lines **ExecStartPre** and **ExecStopPost** to the file so the [Service] section contains:
```
[Service]
EnvironmentFile=-/etc/default/knockd
ExecStartPre=/bin/bash -c 'if [ -f /usr/local/bin/knockd-helper ] ; then /usr/local/bin/knockd-helper start ; fi'
ExecStart=/usr/sbin/knockd $KNOCKD_OPTS
ExecReload=/bin/kill -HUP $MAINPID
ExecStopPost=/bin/bash -c 'if [ -f /usr/local/bin/knockd-helper ] ; then /usr/local/bin/knockd-helper stop ; fi'
KillMode=mixed
SuccessExitStatus=0 2 15
ProtectSystem=full
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN
```

* In order to ensure knockd starts correctly, also change the line:

```
After=network.target
```

to these two lines:

```
After=network.target network-online.target
Wants=network.target network-online.target
```

* Save the file and exit. Reboot the system and check the logs for errors

## Example: Managing an IPSEC VPN with knockd

IPSEC VPNs use two ports. Other VPNs, such as Wireguard (default port: UDP 51820) and OpenVPN (default ports: UDP 1194 and TCP 443), can be knock-enabled in a similar manner.

### /etc/knockd.conf contents

NOTE: The knock ports shown here are only for example. Pick a different set of ports to use!

```
[options]
        UseSyslog

# Initialization: pktables init isakmp --port 500  --udp
#                 pktables init ipsec  --port 4500 --udp
[VPNon]
        sequence = 7000:udp,9001:udp
        seq_timeout = 2
        command = pktables add --service isakmp %IP% ; pktables add --service ipsec %IP%
[VPNoff]
        sequence = 7001:udp,9002:udp
        seq_timeout = 2
        command = pktables delete --service isakmp %IP% ; pktables delete --service ipsec %IP%
```

## Troubleshooting

Port knocking not working? Here are some things to look at.

### Router/Firewall settings

In order for your router/firewall to pass the packets to your host, you'll need to set up port forwardings, one for each port/type combination. So, in the VPN example above, UDP ports 7000, 9001, 7001, 9002 need to be port-forwarded to your VPN server, where knockd is also running.

### Close IPSEC VPN connection before sending "off" port knock

For the IPSEC VPN configuration described above, you MUST disconnect the VPN before sending the VPNoff port knock. Why? When the VPN is connected, packets arriving on the IPSEC server have the tunnel internal IP address rather than the VPN client's external IP address.

This means that you need to remember to VPNoff port knock after disconnecting the VPN. It's a bit annoying, but if you forget to VPNoff port knock, the exposure surface is quite small.

An intruder must:
* Be on the same external IP address from which you port knocked
* Know your VPN server's external IP address
* Have the VPN authentication material. A certificate-secured VPN is significantly more secure than a username/password-secured VPN

## Port Knock Client software

### iOS

The only iOS app I've tried is PortKnock. It's easy to use, and does the job.

### Linux

Here are two ways to get a knock client for Linux
* Use `sudo apt install knockd`. This will install the client `knock` as well as the knockd service (small and installed disabled).
* See portknock.py on this GitHub

### Windows

See portknock.py in this GitHub. Works well with WSL2, Presumably would work from native Windows if Python is installed, but I have not tested this.

As above for Linux (OK...Debian and derivatives), `sudo apt install knockd` also installs the `knock` client

If you need a GUI, I can't help you, but if you find one that you think works well, let me know and i'll add it to this document.

## Additional Notes

iptables is deprecation mode, and will ultimately be phased out completely from Linux. This is actually a compelling reason to use pktables rather than editing iptables commands. At some point (soon) pktables will be updated to use nftables (iptables replacement), and no changes will be required to your knockd configuration.

Port knocking has other uses besides opening and closing ports. For instance, a successful port knock can be used to:
* Reset a problematic service
* Trigger a backup
* Cause a report to be generated and emailed
* Reboot your system
* ... basically anything that can be done with one or more Linux command lines
