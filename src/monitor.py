# coding=utf-8
'''
monitor.py

Using docker client collect metrics,
Foreach the container and check alive containers
for intervals to update container list.

<Main Thread>: startup collector threads & maintain alive containers;
<Collector Threads>: collect container's metrics per thread,
                     if event catched, fire thread or exit it;
'''

import os
import datetime
import yaml
import signal
import time
from client import APIClient
from collector import ContainerAppMetricsCollector
from backend import BackendFactory


# Global live containers
LIVE_CONTAINERS = {}


def sigterm_clean(signum, frame):
    print "Got signal {}..exiting..".format(signum)
    exit(-1)


def main():
    global LIVE_CONTAINERS

    print "CMonitor starting...\n"

    # Workaround for multithread _strptime bug: https://groups.google.com/forum/#!topic/comp.lang.python/VFIppfWTblw
    datetime.datetime.strptime("2015-04-05T14:20:00", "%Y-%m-%dT%H:%M:%S")

    # register signal
    signal.signal(signal.SIGTERM, sigterm_clean)
    signal.signal(signal.SIGINT, sigterm_clean)

    # load configs.
    # TODO: make it as a startup parameter.
    configs = {}
    config_file = os.getenv('CONFIG', '/config/config.yml')
    with open(config_file, 'r') as fp:
        configs = yaml.load(fp)

    cli = APIClient(configs=configs)

    # startup container metrics collector
    check_interval = configs["check_interval"]
    startup_containers = cli.containers()
    for c in startup_containers:
        print "Starting ContainerAppMetricsCollector for {}\n".format(c["Id"])
        app_t = ContainerAppMetricsCollector(c["Id"], configs)
        app_t.setDaemon(True)
        app_t.start()

        LIVE_CONTAINERS[c["Id"]] = [app_t, ]

    print "CMonitor started...\n"
    while True:
        time.sleep(check_interval)

        # Backend housekeeping.
        # We setup a workaround here right now.
        BackendFactory(configs["backend"]["name"]).housekeeping(configs)

        # recollect all live containers states
        # now, we just mark up unknown as offline state.
        cstates = {}
        now_alive_containers = cli.containers()
        for c in now_alive_containers:
            cstates[c["Id"]] = c["State"]

        offlined_containers = set(LIVE_CONTAINERS.keys()) - set(cstates.keys())
        onlined_containers = set(cstates.keys()) - set(LIVE_CONTAINERS.keys())

        # rebuild live container crashed thread.
        for cid, crashed_t in LIVE_CONTAINERS.iteritems():
            if crashed_t[0] is None or not crashed_t[0].is_alive():
                app_t = ContainerAppMetricsCollector(cid, configs)
                app_t.setDaemon(True)
                app_t.start()

                print "Rebuild crashed app metrics thread for {}\n".format(cid)
                LIVE_CONTAINERS[cid][0] = app_t
            else:
                pass

        # offline some
        for offlineId in offlined_containers:
            try:
                LIVE_CONTAINERS[offlineId][0].stop()
                del LIVE_CONTAINERS[offlineId]
                print "Stopped or deleted old container {}\n".format(offlineId)
            except Exception, e:
                print "ERROR while stopping the container {} collector, may already stopped!!!\n".format(offlineId)
                continue

        # online some
        for onlineId in onlined_containers:
            try:
                app_t = ContainerAppMetricsCollector(onlineId, configs)
                app_t.setDaemon(True)
                app_t.start()

                LIVE_CONTAINERS[onlineId] = [app_t, ]
                print "appending new container {}, now lives {}\n".format(onlineId, LIVE_CONTAINERS.keys())
            except Exception, e:
                print "Container {} append to LIVE_CONTAINERS ERROR, {}\n".format(onlineId, e)
                continue


if __name__ == '__main__':
    main()
