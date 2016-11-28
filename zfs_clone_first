#!/usr/bin/python3

import subprocess, shlex

zfs_list = subprocess.check_output(shlex.split('zfs list homePool/home/agents -r -o name -H'), universal_newlines=True)
dataset = 1
for zfs_list_line in zfs_list.splitlines()[1:]:
    zfs_list_snapshots = subprocess.check_output(shlex.split('zfs list -t snapshot -r -o name -H {0}'.format(zfs_list_line)), universal_newlines=True)
    subprocess.call(shlex.split('zfs clone {0} homePool/{1}-clone'.format(zfs_list_snapshots.splitlines()[6], dataset)))
    dataset += 1
