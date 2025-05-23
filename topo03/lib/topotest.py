#!/usr/bin/env python

#
# topotest.py
# Library of helper functions for NetDEF Topology Tests
#
# Copyright (c) 2016 by
# Network Device Education Foundation, Inc. ("NetDEF")
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted, provided
# that the above copyright notice and this permission notice appear
# in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NETDEF DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NETDEF BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
#

import json
import os
import errno
import re
import sys
import functools
import glob
import pwd
import grp
try:
    from StringIO import StringIO ## for Python 2
except ImportError:
    from io import StringIO ## for Python 3

import subprocess
import tempfile
import platform
import difflib
import time

from lib.topolog import logger

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, OVSSwitch, Host
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import Intf

class json_cmp_result(object):
    "json_cmp result class for better assertion messages"

    def __init__(self):
        self.errors = []

    def add_error(self, error):
        "Append error message to the result"
        for line in error.splitlines():
            self.errors.append(line)

    def has_errors(self):
        "Returns True if there were errors, otherwise False."
        return len(self.errors) > 0

def get_test_logdir(node=None, init=False):
    """
    Return the current test log directory based on PYTEST_CURRENT_TEST
    environment variable.
    Optional paramters:
    node:  when set, adds the node specific log directory to the init dir
    init:  when set, initializes the log directory and fixes path permissions
    """
    cur_test = 'test_topo03'

    ret = '/tmp/topotests/' + cur_test
    if node != None:
        dir = ret + "/" + node
    if init:
        os.system('mkdir -p ' + dir)
        os.system('chmod -R go+rw /tmp/topotests')
    return ret

def json_diff(d1, d2):
    """
    Returns a string with the difference between JSON data.
    """
    json_format_opts = {
        'indent': 4,
        'sort_keys': True,
    }
    dstr1 = json.dumps(d1, **json_format_opts)
    dstr2 = json.dumps(d2, **json_format_opts)
    return difflines(dstr2, dstr1, title1='Expected value', title2='Current value', n=0)


def _json_list_cmp(list1, list2, parent, result):
    "Handles list type entries."
    # Check second list2 type
    if not isinstance(list1, type([])) or not isinstance(list2, type([])):
        result.add_error(
            '{} has different type than expected '.format(parent) +
            '(have {}, expected {}):\n{}'.format(
                type(list1), type(list2), json_diff(list1, list2)))
        return

    # Check list size
    if len(list2) > len(list1):
        result.add_error(
            '{} too few items '.format(parent) +
            '(have {}, expected {}:\n {})'.format(
                len(list1), len(list2),
                json_diff(list1, list2)))
        return

    # List all unmatched items errors
    unmatched = []
    for expected in list2:
        matched = False
        for value in list1:
            if json_cmp({'json': value}, {'json': expected}) is None:
                matched = True
                break

        if not matched:
            unmatched.append(expected)

    # If there are unmatched items, error out.
    if unmatched:
        result.add_error(
            '{} value is different (\n{})'.format(
                parent, json_diff(list1, list2)))


def json_cmp(d1, d2):
    """
    JSON compare function. Receives two parameters:
    * `d1`: json value
    * `d2`: json subset which we expect

    Returns `None` when all keys that `d1` has matches `d2`,
    otherwise a string containing what failed.

    Note: key absence can be tested by adding a key with value `None`.
    """
    squeue = [(d1, d2, 'json')]
    result = json_cmp_result()

    for s in squeue:
        nd1, nd2, parent = s

        # Handle JSON beginning with lists.
        if isinstance(nd1, type([])) or isinstance(nd2, type([])):
            _json_list_cmp(nd1, nd2, parent, result)
            if result.has_errors():
                return result
            else:
                return None

        # Expect all required fields to exist.
        s1, s2 = set(nd1), set(nd2)
        s2_req = set([key for key in nd2 if nd2[key] is not None])
        diff = s2_req - s1
        if diff != set({}):
            result.add_error('expected key(s) {} in {} (have {}):\n{}'.format(
                str(list(diff)), parent, str(list(s1)), json_diff(nd1, nd2)))

        for key in s2.intersection(s1):
            # Test for non existence of key in d2
            if nd2[key] is None:
                result.add_error('"{}" should not exist in {} (have {}):\n{}'.format(
                    key, parent, str(s1), json_diff(nd1[key], nd2[key])))
                continue

            # If nd1 key is a dict, we have to recurse in it later.
            if isinstance(nd2[key], type({})):
                if not isinstance(nd1[key], type({})):
                    result.add_error(
                        '{}["{}"] has different type than expected '.format(parent, key) +
                        '(have {}, expected {}):\n{}'.format(
                            type(nd1[key]), type(nd2[key]), json_diff(nd1[key], nd2[key])))
                    continue
                nparent = '{}["{}"]'.format(parent, key)
                squeue.append((nd1[key], nd2[key], nparent))
                continue

            # Check list items
            if isinstance(nd2[key], type([])):
                _json_list_cmp(nd1[key], nd2[key], parent, result)
                continue

            # Compare JSON values
            if nd1[key] != nd2[key]:
                result.add_error(
                    '{}["{}"] value is different (\n{})'.format(
                        parent, key, json_diff(nd1[key], nd2[key])))
                continue

    if result.has_errors():
        return result

    return None


def router_output_cmp(router, cmd, expected):
    """
    Runs `cmd` in router and compares the output with `expected`.
    """
    return difflines(normalize_text(router.vtysh_cmd(cmd)),
                     normalize_text(expected),
                     title1="Current output",
                     title2="Expected output")


def router_json_cmp(router, cmd, data):
    """
    Runs `cmd` that returns JSON data (normally the command ends with 'json')
    and compare with `data` contents.
    """
    return json_cmp(router.vtysh_cmd(cmd, isjson=True), data)


def run_and_expect(func, what, count=20, wait=3):
    """
    Run `func` and compare the result with `what`. Do it for `count` times
    waiting `wait` seconds between tries. By default it tries 20 times with
    3 seconds delay between tries.

    Returns (True, func-return) on success or
    (False, func-return) on failure.

    ---

    Helper functions to use with this function:
    - router_output_cmp
    - router_json_cmp
    """
    start_time = time.time()
    func_name = "<unknown>"
    if func.__class__ == functools.partial:
        func_name = func.func.__name__
    else:
        func_name = func.__name__

    logger.info(
        "'{}' polling started (interval {} secs, maximum wait {} secs)".format(
            func_name, wait, int(wait * count)))

    while count > 0:
        result = func()
        if result != what:
            time.sleep(wait)
            count -= 1
            continue

        end_time = time.time()
        logger.info("'{}' succeeded after {:.2f} seconds".format(
            func_name, end_time - start_time))
        return (True, result)

    end_time = time.time()
    logger.error("'{}' failed after {:.2f} seconds".format(
        func_name, end_time - start_time))
    return (False, result)


def int2dpid(dpid):
    "Converting Integer to DPID"

    try:
        dpid = hex(dpid)[2:]
        dpid = '0'*(16-len(dpid))+dpid
        return dpid
    except IndexError:
        raise Exception('Unable to derive default datapath ID - '
                        'please either specify a dpid or use a '
                        'canonical switch name such as s23.')

def pid_exists(pid):
    "Check whether pid exists in the current process table."

    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    else:
        return True

def get_textdiff(text1, text2, title1="", title2="", **opts):
    "Returns empty string if same or formatted diff"

    diff = '\n'.join(difflib.unified_diff(text1, text2,
           fromfile=title1, tofile=title2, **opts))
    # Clean up line endings
    diff = os.linesep.join([s for s in diff.splitlines() if s])
    return diff

def difflines(text1, text2, title1='', title2='', **opts):
    "Wrapper for get_textdiff to avoid string transformations."
    text1 = ('\n'.join(text1.rstrip().splitlines()) + '\n').splitlines(1)
    text2 = ('\n'.join(text2.rstrip().splitlines()) + '\n').splitlines(1)
    return get_textdiff(text1, text2, title1, title2, **opts)

def get_file(content):
    """
    Generates a temporary file in '/tmp' with `content` and returns the file name.
    """
    fde = tempfile.NamedTemporaryFile(mode='w', delete=False)
    fname = fde.name
    fde.write(content)
    fde.close()
    return fname

def normalize_text(text):
    """
    Strips formating spaces/tabs, carriage returns and trailing whitespace.
    """
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\r', '', text)

    # Remove whitespace in the middle of text.
    text = re.sub(r'[ \t]+\n', '\n', text)
    # Remove whitespace at the end of the text.
    text = text.rstrip()

    return text

def module_present(module, load=True):
    """
    Returns whether `module` is present.

    If `load` is true, it will try to load it via modprobe.
    """
    with open('/proc/modules', 'r') as modules_file:
        if module.replace('-','_') in modules_file.read():
            return True
    cmd = '/sbin/modprobe {}{}'.format('' if load else '-n ',
                                       module)
    if os.system(cmd) != 0:
        return False
    else:
        return True

def version_cmp(v1, v2):
    """
    Compare two version strings and returns:

    * `-1`: if `v1` is less than `v2`
    * `0`: if `v1` is equal to `v2`
    * `1`: if `v1` is greater than `v2`

    Raises `ValueError` if versions are not well formated.
    """
    vregex = r'(?P<whole>\d+(\.(\d+))*)'
    v1m = re.match(vregex, v1)
    v2m = re.match(vregex, v2)
    if v1m is None or v2m is None:
        raise ValueError("got a invalid version string")

    # Split values
    v1g = v1m.group('whole').split('.')
    v2g = v2m.group('whole').split('.')

    # Get the longest version string
    vnum = len(v1g)
    if len(v2g) > vnum:
        vnum = len(v2g)

    # Reverse list because we are going to pop the tail
    v1g.reverse()
    v2g.reverse()
    for _ in range(vnum):
        try:
            v1n = int(v1g.pop())
        except IndexError:
            while v2g:
                v2n = int(v2g.pop())
                if v2n > 0:
                    return -1
            break

        try:
            v2n = int(v2g.pop())
        except IndexError:
            if v1n > 0:
                return 1
            while v1g:
                v1n = int(v1g.pop())
                if v1n > 0:
                    return 1
            break

        if v1n > v2n:
            return 1
        if v1n < v2n:
            return -1
    return 0

def interface_set_status(node, ifacename, ifaceaction=False, vrf_name=None):
    if ifaceaction:
        str_ifaceaction = 'no shutdown'
    else:
        str_ifaceaction = 'shutdown'
    if vrf_name == None:
        cmd = 'vtysh -c \"configure terminal\" -c \"interface {0}\" -c \"{1}\"'.format(ifacename, str_ifaceaction)
    else:
        cmd = 'vtysh -c \"configure terminal\" -c \"interface {0} vrf {1}\" -c \"{2}\"'.format(ifacename, vrf_name, str_ifaceaction)
    node.run(cmd)

def ip4_route_zebra(node, vrf_name=None):
    """
    Gets an output of 'show ip route' command. It can be used
    with comparing the output to a reference
    """
    if vrf_name == None:
        tmp = node.vtysh_cmd('show ip route')
    else:
        tmp = node.vtysh_cmd('show ip route vrf {0}'.format(vrf_name))
    output = re.sub(r" [0-2][0-9]:[0-5][0-9]:[0-5][0-9]", " XX:XX:XX", tmp)

    lines = output.splitlines()
    header_found = False
    while lines and (not lines[0].strip() or not header_found):
        if '> - selected route' in lines[0]:
            header_found = True
        lines = lines[1:]
    return '\n'.join(lines)

def proto_name_to_number(protocol):
    return {
        'bgp':    '186',
        'isis':   '187',
        'ospf':   '188',
        'rip':    '189',
        'ripng':  '190',
        'nhrp':   '191',
        'eigrp':  '192',
        'ldp':    '193',
        'sharp':  '194',
        'pbr':    '195',
        'static': '196'
    }.get(protocol, protocol)  # default return same as input


def ip4_route(node):
    """
    Gets a structured return of the command 'ip route'. It can be used in
    conjuction with json_cmp() to provide accurate assert explanations.

    Return example:
    {
        '10.0.1.0/24': {
            'dev': 'eth0',
            'via': '172.16.0.1',
            'proto': '188',
        },
        '10.0.2.0/24': {
            'dev': 'eth1',
            'proto': 'kernel',
        }
    }
    """
    output = normalize_text(node.run('ip route')).splitlines()
    result = {}
    for line in output:
        columns = line.split(' ')
        route = result[columns[0]] = {}
        prev = None
        for column in columns:
            if prev == 'dev':
                route['dev'] = column
            if prev == 'via':
                route['via'] = column
            if prev == 'proto':
                # translate protocol names back to numbers
                route['proto'] = proto_name_to_number(column)
            if prev == 'metric':
                route['metric'] = column
            if prev == 'scope':
                route['scope'] = column
            prev = column

    return result

def ip6_route(node):
    """
    Gets a structured return of the command 'ip -6 route'. It can be used in
    conjuction with json_cmp() to provide accurate assert explanations.

    Return example:
    {
        '2001:db8:1::/64': {
            'dev': 'eth0',
            'proto': '188',
        },
        '2001:db8:2::/64': {
            'dev': 'eth1',
            'proto': 'kernel',
        }
    }
    """
    output = normalize_text(node.run('ip -6 route')).splitlines()
    result = {}
    for line in output:
        columns = line.split(' ')
        route = result[columns[0]] = {}
        prev = None
        for column in columns:
            if prev == 'dev':
                route['dev'] = column
            if prev == 'via':
                route['via'] = column
            if prev == 'proto':
                # translate protocol names back to numbers
                route['proto'] = proto_name_to_number(column)
            if prev == 'metric':
                route['metric'] = column
            if prev == 'pref':
                route['pref'] = column
            prev = column

    return result

def sleep(amount, reason=None):
    """
    Sleep wrapper that registers in the log the amount of sleep
    """
    if reason is None:
        logger.info('Sleeping for {} seconds'.format(amount))
    else:
        logger.info(reason + ' ({} seconds)'.format(amount))

    time.sleep(amount)

def checkAddressSanitizerError(output, router, component):
    "Checks for AddressSanitizer in output. If found, then logs it and returns true, false otherwise"

    addressSantizerError = re.search('(==[0-9]+==)ERROR: AddressSanitizer: ([^\s]*) ', output)
    if addressSantizerError:
        sys.stderr.write("%s: %s triggered an exception by AddressSanitizer\n" % (router, component))
        # Sanitizer Error found in log
        pidMark = addressSantizerError.group(1)
        addressSantizerLog = re.search('%s(.*)%s' % (pidMark, pidMark), output, re.DOTALL)
        if addressSantizerLog:
            callingTest = os.path.basename(sys._current_frames().values()[0].f_back.f_back.f_globals['__file__'])
            callingProc = sys._getframe(2).f_code.co_name
            with open("/tmp/AddressSanitzer.txt", "a") as addrSanFile:
                sys.stderr.write('\n'.join(addressSantizerLog.group(1).splitlines()) + '\n')
                addrSanFile.write("## Error: %s\n\n" % addressSantizerError.group(2))
                addrSanFile.write("### AddressSanitizer error in topotest `%s`, test `%s`, router `%s`\n\n" % (callingTest, callingProc, router))
                addrSanFile.write('    '+ '\n    '.join(addressSantizerLog.group(1).splitlines()) + '\n')
                addrSanFile.write("\n---------------\n")
        return True
    return False

def addRouter(topo, name):
    "Adding a FRRouter (or Quagga) to Topology"

    MyPrivateDirs = ['/etc/frr',
                         '/etc/quagga',
                         '/var/run/frr',
                         '/var/run/quagga',
                         '/var/log']
    return topo.addNode(name, cls=Router, privateDirs=MyPrivateDirs)

def set_sysctl(node, sysctl, value):
    "Set a sysctl value and return None on success or an error string"
    valuestr = '{}'.format(value)
    command = "sysctl {0}={1}".format(sysctl, valuestr)
    cmdret = node.cmd(command)

    matches = re.search(r'([^ ]+) = ([^\s]+)', cmdret)
    if matches is None:
        return cmdret
    if matches.group(1) != sysctl:
        return cmdret
    if matches.group(2) != valuestr:
        return cmdret

    return None

def assert_sysctl(node, sysctl, value):
    "Set and assert that the sysctl is set with the specified value."
    assert set_sysctl(node, sysctl, value) is None

class LinuxRouter(Node):
    "A Node with IPv4/IPv6 forwarding enabled."

    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        # Enable forwarding on the router
        assert_sysctl(self, 'net.ipv4.ip_forward', 1)
        assert_sysctl(self, 'net.ipv6.conf.all.forwarding', 1)
    def terminate(self):
        """
        Terminate generic LinuxRouter Mininet instance
        """
        set_sysctl(self, 'net.ipv4.ip_forward', 0)
        set_sysctl(self, 'net.ipv6.conf.all.forwarding', 0)
        super(LinuxRouter, self).terminate()

class Router(Node):
    "A Node with IPv4/IPv6 forwarding enabled and Quagga as Routing Engine"

    def __init__(self, name, **params):
        super(Router, self).__init__(name, **params)
        self.logdir = params.get('logdir', get_test_logdir(name, True))
        self.daemondir = None
        self.hasmpls = False
        self.routertype = 'frr'
        self.daemons = {'zebra': 0, 'ripd': 0, 'ripngd': 0, 'ospfd': 0,
                        'ospf6d': 0, 'isisd': 0, 'bgpd': 0, 'pimd': 0,
                        'ldpd': 0, 'eigrpd': 0, 'nhrpd': 0, 'staticd': 0,
                        'bfdd': 0}
        self.daemons_options = {'zebra': ''}
        self.reportCores = True
        self.version = None

    def _config_frr(self, **params):
        "Configure FRR binaries"
        self.daemondir = params.get('frrdir')
        if self.daemondir is None:
            self.daemondir = '/usr/lib/frr'

        zebra_path = os.path.join(self.daemondir, 'zebra')
        if not os.path.isfile(zebra_path):
            raise Exception("FRR zebra binary doesn't exist at {}".format(zebra_path))

    def _config_quagga(self, **params):
        "Configure Quagga binaries"
        self.daemondir = params.get('quaggadir')
        if self.daemondir is None:
            self.daemondir = '/usr/lib/quagga'

        zebra_path = os.path.join(self.daemondir, 'zebra')
        if not os.path.isfile(zebra_path):
            raise Exception("Quagga zebra binary doesn't exist at {}".format(zebra_path))

    # pylint: disable=W0221
    # Some params are only meaningful for the parent class.
    def config(self, **params):
        super(Router, self).config(**params)

        # User did not specify the daemons directory, try to autodetect it.
        self.daemondir = params.get('daemondir')
        if self.daemondir is None:
            self.routertype = params.get('routertype', 'frr')
            if self.routertype == 'quagga':
                self._config_quagga(**params)
            else:
                self._config_frr(**params)
        else:
            # Test the provided path
            zpath = os.path.join(self.daemondir, 'zebra')
            if not os.path.isfile(zpath):
                raise Exception('No zebra binary found in {}'.format(zpath))
            # Allow user to specify routertype when the path was specified.
            if params.get('routertype') is not None:
                self.routertype = self.params.get('routertype')

        # Enable forwarding on the router
        assert_sysctl(self, 'net.ipv4.ip_forward', 1)
        assert_sysctl(self, 'net.ipv6.conf.all.forwarding', 1)
        # Enable coredumps
        assert_sysctl(self, 'kernel.core_uses_pid', 1)
        assert_sysctl(self, 'fs.suid_dumpable', 1)
        #this applies to the kernel not the namespace...
        #original on ubuntu 17.x, but apport won't save as in namespace
        # |/usr/share/apport/apport %p %s %c %d %P
        corefile = '%e_core-sig_%s-pid_%p.dmp'
        assert_sysctl(self, 'kernel.core_pattern', corefile)
        self.cmd('ulimit -c unlimited')
        # Set ownership of config files
        self.cmd('chown {0}:{0}vty /etc/{0}'.format(self.routertype))

    def terminate(self):
        # Delete Running Quagga or FRR Daemons
        self.stopRouter()
        # rundaemons = self.cmd('ls -1 /var/run/%s/*.pid' % self.routertype)
        # for d in StringIO.StringIO(rundaemons):
        #     self.cmd('kill -7 `cat %s`' % d.rstrip())
        #     self.waitOutput()
        # Disable forwarding
        set_sysctl(self, 'net.ipv4.ip_forward', 0)
        set_sysctl(self, 'net.ipv6.conf.all.forwarding', 0)
        super(Router, self).terminate()
        os.system('chmod -R go+rw /tmp/topotests')

    def stopRouter(self, wait=True, assertOnError=True, minErrorVersion='5.1'):
        # Stop Running Quagga or FRR Daemons
        rundaemons = self.cmd('ls -1 /var/run/%s/*.pid' % self.routertype)
        errors = ""
        if re.search(r"No such file or directory", rundaemons):
            return errors
        if rundaemons is not None:
            numRunning = 0
            for d in StringIO(rundaemons):
                daemonpid = self.cmd('cat %s' % d.rstrip()).rstrip()
                if (daemonpid.isdigit() and pid_exists(int(daemonpid))):
                    logger.info('{}: stopping {}'.format(
                        self.name,
                        os.path.basename(d.rstrip().rsplit(".", 1)[0])
                    ))
                    self.cmd('kill -TERM %s' % daemonpid)
                    self.waitOutput()
                    if pid_exists(int(daemonpid)):
                        numRunning += 1
            if wait and numRunning > 0:
                sleep(2, '{}: waiting for daemons stopping'.format(self.name))
                # 2nd round of kill if daemons didn't exit
                for d in StringIO(rundaemons):
                    daemonpid = self.cmd('cat %s' % d.rstrip()).rstrip()
                    if (daemonpid.isdigit() and pid_exists(int(daemonpid))):
                        logger.info('{}: killing {}'.format(
                            self.name,
                            os.path.basename(d.rstrip().rsplit(".", 1)[0])
                        ))
                        self.cmd('kill -7 %s' % daemonpid)
                        self.waitOutput()
                    self.cmd('rm -- {}'.format(d.rstrip()))
        if wait:
                errors = self.checkRouterCores(reportOnce=True)
                if self.checkRouterVersion('<', minErrorVersion):
                    #ignore errors in old versions
                    errors = ""
                if assertOnError and len(errors) > 0:
                    assert "Errors found - details follow:" == 0, errors
        return errors

    def removeIPs(self):
        for interface in self.intfNames():
            self.cmd('ip address flush', interface)

    def checkCapability(self, daemon, param):
        if param is not None:
            daemon_path = os.path.join(self.daemondir, daemon)
            daemon_search_option = param.replace('-','')
            output = self.cmd('{0} -h | grep {1}'.format(
                daemon_path, daemon_search_option))
            if daemon_search_option not in output:
                return False
        return True


    def startRouter(self,source=None, tgen=None):
        # Disable integrated-vtysh-config
        self.cmd('echo "no service integrated-vtysh-config" >> /etc/%s/vtysh.conf' % self.routertype)
        self.cmd('chown %s:%svty /etc/%s/vtysh.conf' % (self.routertype, self.routertype, self.routertype))
        # TODO remove the following lines after all tests are migrated to Topogen.
        # Try to find relevant old logfiles in /tmp and delete them
        map(os.remove, glob.glob('{}/{}/*.log'.format(self.logdir, self.name)))
        # Remove old core files
        map(os.remove, glob.glob('{}/{}/*.dmp'.format(self.logdir, self.name)))
        # Remove IP addresses from OS first - we have them in zebra.conf
        self.removeIPs()
   

        if self.daemons['eigrpd'] == 1:
            eigrpd_path = os.path.join(self.daemondir, 'eigrpd')
            if not os.path.isfile(eigrpd_path):
                logger.info("EIGRP Test, but no eigrpd compiled or installed")
                return "EIGRP Test, but no eigrpd compiled or installed"

        if self.daemons['bfdd'] == 1:
            bfdd_path = os.path.join(self.daemondir, 'bfdd')
            if not os.path.isfile(bfdd_path):
                logger.info("BFD Test, but no bfdd compiled or installed")
                return "BFD Test, but no bfdd compiled or installed"

        self.restartRouter(source)
        return ""
    def startRIPD(self, source=None):
        self.cmd('cd {}/{}'.format(self.logdir, self.name))
        self.cmd('umask 000')
        ripd_path = os.path.join(self.daemondir, 'ripd')
        self.cmd('{0} --config_file ./ripd.conf --pid_file ./ripd.pid -z ./zebra.api &'.format(ripd_path))

    def startBGPD(self, source=None):
        self.cmd('cd {}/{}'.format(self.logdir, self.name))
        self.cmd('umask 000')
        bgpd_path = os.path.join(self.daemondir, 'bgpd')
        self.cmd('{0} --config_file ./bgpd.conf --pid_file ./bgpd.pid -z ./zebra.api &'.format(bgpd_path))
	
                
    def restartRouter(self, source=None):
        # Starts actual daemons without init (ie restart)
        # cd to per node directory
        self.cmd('cd {}/{}'.format(self.logdir, self.name))
        self.cmd('umask 000')
        #Re-enable to allow for report per run
        self.reportCores = True
        
        if self.version == None:
            self.version = self.cmd(os.path.join(self.daemondir, 'bgpd')+' -v').split()[2]
            logger.info('{}: running version: {}'.format(self.name,self.version))
            
        # Start Zebra first
        zebra_path = os.path.join(self.daemondir, 'zebra')
     
        path = './'.format(self.name)
        os.chmod(path, 0o777)
        uid = pwd.getpwnam("frr").pw_uid
        gid = grp.getgrnam("frr").gr_gid
        self.cmd('pwd');
        os.chown(path, uid, gid)  
        
        self.cmd('cp {0}/{1}/zebra.conf ./'.format(source,self.name))
        self.cmd('cp {0}/{1}/ripd.conf ./'.format(source,self.name))
        self.cmd('cp {0}/{1}/bgpd.conf ./'.format(source,self.name))
        
        self.cmd('{0} --config_file ./zebra.conf --daemon --pid_file ./zebra.pid -z ./zebra.api &'.format(
         zebra_path
        ))
        self.waitOutput()
        logger.debug('{}: {} zebra started'.format(self, self.routertype))
        

       
       # Fix Link-Local Addresses
        # Somehow (on Mininet only), Zebra removes the IPv6 Link-Local addresses on start. Fix this
        self.cmd('for i in `ls /sys/class/net/` ; do mac=`cat /sys/class/net/$i/address`; IFS=\':\'; set $mac; unset IFS; ip address add dev $i scope link fe80::$(printf %02x $((0x$1 ^ 2)))$2:${3}ff:fe$4:$5$6/64; done')
        # Now start all the other daemons
        for daemon in self.daemons:
            # Skip disabled daemons and zebra
            if self.daemons[daemon] == 0 or daemon == 'zebra' or daemon == 'staticd':
                continue
            daemon_path = os.path.join(self.daemondir, daemon)
            self.cmd('{0} {1} > {2}.out 2> {2}.err &'.format(
                daemon_path, self.daemons_options.get(daemon, ''), daemon
            ))
            self.waitOutput()
            logger.debug('{}: {} {} started'.format(self, self.routertype, daemon))
    def getStdErr(self, daemon):
        return self.getLog('err', daemon)
    def getStdOut(self, daemon):
        return self.getLog('out', daemon)
    def getLog(self, log, daemon):
        return self.cmd('cat {}/{}/{}.{}'.format(self.logdir, self.name, daemon, log))



    def checkRouterCores(self, reportLeaks=True, reportOnce=False):
        if reportOnce and not self.reportCores:
            return
        reportMade = False
        traces = ""
        for daemon in self.daemons:
            if (self.daemons[daemon] == 1):
                # Look for core file
                corefiles = glob.glob('{}/{}/{}_core*.dmp'.format(
                    self.logdir, self.name, daemon))
                if (len(corefiles) > 0):
                    daemon_path = os.path.join(self.daemondir, daemon)
                    backtrace = subprocess.check_output([
                        "gdb {} {} --batch -ex bt 2> /dev/null".format(daemon_path, corefiles[0])
                    ], shell=True)
                    sys.stderr.write("\n%s: %s crashed. Core file found - Backtrace follows:\n" % (self.name, daemon))
                    sys.stderr.write("%s" % backtrace)
                    traces = traces + "\n%s: %s crashed. Core file found - Backtrace follows:\n%s" % (self.name, daemon, backtrace)
                    reportMade = True
                elif reportLeaks:
                    log = self.getStdErr(daemon)
                    if "memstats" in log:
                        sys.stderr.write("%s: %s has memory leaks:\n" % (self.name, daemon))
                        traces = traces + "\n%s: %s has memory leaks:\n" % (self.name, daemon)
                        log = re.sub("core_handler: ", "", log)
                        log = re.sub(r"(showing active allocations in memory group [a-zA-Z0-9]+)", r"\n  ## \1", log)
                        log = re.sub("memstats:  ", "    ", log)
                        sys.stderr.write(log)
                        reportMade = True
                # Look for AddressSanitizer Errors and append to /tmp/AddressSanitzer.txt if found
                if checkAddressSanitizerError(self.getStdErr(daemon), self.name, daemon):
                    sys.stderr.write("%s: Daemon %s killed by AddressSanitizer" % (self.name, daemon))
                    traces = traces + "\n%s: Daemon %s killed by AddressSanitizer" % (self.name, daemon)
                    reportMade = True
        if reportMade:
            self.reportCores = False
        return traces

   
    def get_ipv6_linklocal(self):
        "Get LinkLocal Addresses from interfaces"

        linklocal = []

        ifaces = self.cmd('ip -6 address')
        # Fix newlines (make them all the same)
        ifaces = ('\n'.join(ifaces.splitlines()) + '\n').splitlines()
        interface=""
        ll_per_if_count=0
        for line in ifaces:
            m = re.search('[0-9]+: ([^:@]+)[@if0-9:]+ <', line)
            if m:
                interface = m.group(1)
                ll_per_if_count = 0
            m = re.search('inet6 (fe80::[0-9a-f]+:[0-9a-f]+:[0-9a-f]+:[0-9a-f]+)[/0-9]* scope link', line)
            if m:
                local = m.group(1)
                ll_per_if_count += 1
                if (ll_per_if_count > 1):
                    linklocal += [["%s-%s" % (interface, ll_per_if_count), local]]
                else:
                    linklocal += [[interface, local]]
        return linklocal
    def daemon_available(self, daemon):
        "Check if specified daemon is installed (and for ldp if kernel supports MPLS)"

        daemon_path = os.path.join(self.daemondir, daemon)
        if not os.path.isfile(daemon_path):
            return False
        if (daemon == 'ldpd'):
            if version_cmp(platform.release(), '4.5') < 0:
                return False
            if not module_present('mpls-router', load=False):
                return False
            if not module_present('mpls-iptunnel', load=False):
                return False
        return True

    def get_routertype(self):
        "Return the type of Router (frr or quagga)"

        return self.routertype
    def report_memory_leaks(self, filename_prefix, testscript):
        "Report Memory Leaks to file prefixed with given string"

        leakfound = False
        filename = filename_prefix + re.sub(r"\.py", "", testscript) + ".txt"
        for daemon in self.daemons:
            if (self.daemons[daemon] == 1):
                log = self.getStdErr(daemon)
                if "memstats" in log:
                    # Found memory leak
                    logger.info('\nRouter {} {} StdErr Log:\n{}'.format(
                        self.name, daemon, log))
                    if not leakfound:
                        leakfound = True
                        # Check if file already exists
                        fileexists = os.path.isfile(filename)
                        leakfile = open(filename, "a")
                        if not fileexists:
                            # New file - add header
                            leakfile.write("# Memory Leak Detection for topotest %s\n\n" % testscript)
                        leakfile.write("## Router %s\n" % self.name)
                    leakfile.write("### Process %s\n" % daemon)
                    log = re.sub("core_handler: ", "", log)
                    log = re.sub(r"(showing active allocations in memory group [a-zA-Z0-9]+)", r"\n#### \1\n", log)
                    log = re.sub("memstats:  ", "    ", log)
                    leakfile.write(log)
                    leakfile.write("\n")
        if leakfound:
            leakfile.close()


class LegacySwitch(OVSSwitch):
    "A Legacy Switch without OpenFlow"

    def __init__(self, name, **params):
        OVSSwitch.__init__(self, name, failMode='standalone', **params)
        self.switchIP = None

