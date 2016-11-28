#!/usr/bin/python3

import time, datetime, shlex, subprocess, os, configparser, argparse, re, statistics, sys

# Set up argparser and parse args
argparser = argparse.ArgumentParser(description='Script for testing zfs')
argparser.add_argument('CONFIG_FILE', help='you must supply a config file')
argparser.add_argument('-s', '--setup', help='setup test environment', action='store_true')
argparser.add_argument('-r', '--run', help='run tests', action='store_true')
argparser.add_argument('-c', '--cleanup', help='cleanup everything', action='store_true')
args = argparser.parse_args()

# Get config from ConfigParser
config = configparser.SafeConfigParser(interpolation=configparser.ExtendedInterpolation())
config.read(args.CONFIG_FILE)

def setup():

    setupStartTime = datetime.datetime.now()
    source = config.get('setup', 'source').strip()
    datasets = [config.get('setup', dataset).strip() for dataset in config.options('setup') if dataset.startswith('dataset_')]

    with open('/datto/config/inhibitAllCron', 'w') as inhibitAllCron:
        pass    

    for dataset in datasets:
        subprocess.call(shlex.split('recvResume.sh -s {0} -d homePool/home/agents/{1} -l root'.format(source, dataset)))

    os.remove('/datto/config/inhibitAllCron')

    setupEndTime = datetime.datetime.now()
    setupElapsedTimeSeconds = (setupEndTime - setupStartTime).seconds
    print('\nSetup took {0} seconds\n'.format(setupElapsedTimeSeconds))

def cleanup():

    cleanupStartTime = datetime.datetime.now()
    datasets = [config.get('setup', dataset).strip() for dataset in config.options('setup') if dataset.startswith('dataset_')]

    with open('/datto/config/inhibitAllCron', 'w') as inhibitAllCron:
        pass

    for dataset in datasets:
        subprocess.call(shlex.split('zfs destroy -R homePool/home/agents/{0}'.format(dataset)))

    os.remove('/datto/config/inhibitAllCron')
    
    cleanupEndTime = datetime.datetime.now()
    cleanupElapsedTimeSeconds = (cleanupEndTime - cleanupStartTime).seconds
    print('\nCleanup took {0} seconds\n'.format(cleanupElapsedTimeSeconds))

def getArcSize():
    
    with open('/proc/spl/kstat/zfs/arcstats') as arcstats:
        output = arcstats.read()
    regex = re.compile(r'(\bsize\b)\s+4\s+(\d+)')
    match = regex.search(output)
    size = int(match.group(2))
    return size

def getIO():
    
    process = subprocess.Popen(shlex.split('zpool iostat -y'), universal_newlines=True, stdout=subprocess.PIPE)
    output = process.communicate()[0]
    regex = re.compile(r'(\d+\.?\d{0,2}?)([a-zA-Z])?\s+(\d+\.?\d{0,2}?)([a-zA-Z])?$')
    match = regex.search(output)
    
    if match.group(2) == 'K':
        read = float(match.group(1)) * 1024
    elif match.group(2) == 'M':
        read = float(match.group(1)) * 1048576
    else:
        read = float(match.group(1))
    
    if match.group(4) == 'K':
        write = float(match.group(3)) * 1024
    elif match.group(4) == 'M':
        write = float(match.group(3)) * 1048576
    else:
        write = float(match.group(3))
    
    return (read, write)

def getMem():
    
    process = subprocess.Popen(shlex.split('free -b -w'), universal_newlines=True, stdout=subprocess.PIPE)
    output = process.communicate()[0]
    regex = re.compile(r'Mem:\s+\d+\s+(\d+)')
    match = regex.search(output)
    used = int(match.group(1))
    return used

def getCPU():
    
    process = subprocess.Popen(shlex.split('mpstat 1 1'), universal_newlines=True, stdout=subprocess.PIPE)
    output = process.communicate()[0]
    regex = re.compile(r'Average:\s+all\s+(\d{1,3}\.\d{2})\s+(\d{1,3}\.\d{2})\s+(\d{1,3}\.\d{2})\s+(\d{1,3}\.\d{2})')
    match = regex.search(output)
    usr = float(match.group(1))
    sys = float(match.group(3))
    iowait = float(match.group(4))
    return (usr, sys, iowait)

def getDedup():
    
    process = subprocess.Popen(shlex.split('zpool list'), universal_newlines=True, stdout=subprocess.PIPE)
    output = process.communicate()[0]
    regex = re.compile(r'(\d{1,3}\.\d{2})x\s+\w+\s+-$')
    match = regex.search(output)
    dedup = float(match.group(1))
    return dedup

def getLoadAvg():

    with open('/proc/loadavg') as loadavg:
        output = loadavg.read()
    regex = re.compile(r'(^\d+\.\d+)')
    match = regex.search(output)
    load = float(match.group(1))
    return load

def run():
    
    runProcessList = []
    
    arcSizeList = []
    readIOList = []
    writeIOList = []
    usedMemList = []
    usrCPUList = []
    sysCPUList = []
    iowaitCPUList = []
    dedupList = []
    loadAvgList = []
    
    runStartTime = datetime.datetime.now()

    for section in config.sections():
        if section.startswith('batch_'):
            test = [config.get(section, options) for options in config.options(section) if options.startswith('p_')]

            for command in test:
                runProcessList.append(subprocess.Popen(shlex.split(command), stdout=subprocess.DEVNULL))

            while runProcessList:

                arcSizeList.append(getArcSize())
                readIOList.append(getIO()[0])
                writeIOList.append(getIO()[1])
                usedMemList.append(getMem())
                usrCPUList.append(getCPU()[0])
                sysCPUList.append(getCPU()[1])
                iowaitCPUList.append(getCPU()[2])
                dedupList.append(getDedup())
                loadAvgList.append(getLoadAvg())

                for process in runProcessList:
                    process.poll()
                    if process.returncode is None:
                        pass
                    elif process.returncode == 0:
                        runProcessList.remove(process)
                    else:
                        sys.exit('A process in the test exited with non-zero code.')
            
    runEndTime = datetime.datetime.now()
    runElapsedTimeSeconds = (runEndTime - runStartTime).seconds
    
    print('\n{0:^42}\n'.format('---Summary---'))
    print('{0:^24}{1}'.format('Run Start Time', runStartTime))
    print('{0:^24}{1}'.format('Run End Time', runEndTime))    
    print('{0:^24}{1} seconds\n'.format('Total Run Time', runElapsedTimeSeconds))
    
    headers = ('METRIC', 'MIN', 'MAX', 'AVG')
    spacers = ('---', '---', '---', '---')
    template = '{0:^20}{1:^20}{2:^20}{3:^20}'
    num_template = '{0:^20}{1:^20.2f}{2:^20.2f}{3:^20.2f}'

    BYTES_IN_MB = 1048576
    
    arcSizeResults = ('Arc Size (MB)', min(arcSizeList)/BYTES_IN_MB, max(arcSizeList)/BYTES_IN_MB, statistics.mean(arcSizeList)/BYTES_IN_MB)
    readSpeedResults = ('Read Speed (MB/s)', min(readIOList)/BYTES_IN_MB, max(readIOList)/BYTES_IN_MB, statistics.mean(readIOList)/BYTES_IN_MB)
    writeSpeedResults = ('Write Speed (MB/s)', min(writeIOList)/BYTES_IN_MB, max(writeIOList)/BYTES_IN_MB, statistics.mean(writeIOList)/BYTES_IN_MB)
    usedMemResults = ('Used Memory (MB)', min(usedMemList)/BYTES_IN_MB, max(usedMemList)/BYTES_IN_MB, statistics.mean(usedMemList)/BYTES_IN_MB)
    usrCPUResults = ('User CPU (%)', min(usrCPUList), max(usrCPUList), statistics.mean(usrCPUList))
    sysCPUResults = ('System CPU (%)', min(sysCPUList), max(sysCPUList), statistics.mean(sysCPUList))
    iowaitCPUResults = ('CPU IO Wait (%)', min(iowaitCPUList), max(iowaitCPUList), statistics.mean(iowaitCPUList))
    dedupResults = ('Dedup Ratio (x)', min(dedupList), max(dedupList), statistics.mean(dedupList))    
    loadAvgResults = ('Load Avg', min(loadAvgList), max(loadAvgList), statistics.mean(loadAvgList))

    print(template.format(*headers))
    print(template.format(*spacers))
    for results in (arcSizeResults, readSpeedResults, writeSpeedResults, usedMemResults, usrCPUResults, sysCPUResults, iowaitCPUResults, dedupResults, loadAvgResults):
        print(num_template.format(*results))
    print('\n')

if args.setup:
    setup()

if args.run:
    run()

if args.cleanup:
    cleanup()
