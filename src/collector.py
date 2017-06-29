# coding=utf-8

import threading
import time
from client import APIClient
from backend import BackendFactory


class MetricsCollector(threading.Thread):
    def __init__(self, container_id, configs={}):
        '''
        MetricsCollector is a collector for container metrics.
        It collects metrics via registerd modules in configs.
        And save data into specified backends.

        MetricsCollector will be spawned at the startup point,
        and keep one container to one collector pattern.
        '''
        self.container_id = container_id
        self.stopped = False
        self.configs = configs

        super(MetricsCollector, self).__init__()

    def stop(self):
        self.stopped = True

    def is_alive(self):
        return True if not self.stopped else False

    def collect(self):
        pass

    def run(self):
        while not self.stopped:
            self.collect()

        print "Thread for {} normally exited..".format(self.container_id)


class ContainerAppMetricsCollector(MetricsCollector):
    '''
    ContainerAppMetricsCollector is a metrics collector in app level,
    it collects metrics via `docker exec`.
    '''
    def __init__(self, container_id, configs={}):
        # initial backend.
        self.backend = BackendFactory(configs["backend"]["name"])(
            configs=configs
        )

        self.interval = configs["collect_interval"]
        self.client = APIClient(configs)
        self.configs = configs

        # initial modules.
        # query the CMonitor configured modules,
        # and sync them into application container.
        self.client.sync_modules(container_id)

        super(ContainerAppMetricsCollector, self).__init__(container_id,
                                                           configs)

    def execute(self):
        '''
        Execute the registered modules, and collect the returned metrics.
        TODO: there could be some filters here.
        '''
        registered_modules = self.configs["registered_modules"]

        data = {}
        for reg_key, mod in registered_modules.iteritems():
            ret = self.client.exec_module(self.container_id, mod["name"])
            data[mod["name"]] = ret
        return data

    def collect(self):
        try:
            time.sleep(self.interval)

            ret = self.execute()

            # exec executor.
            # we currently make it sync run.
            # TODO: make a executor pattern to cocurrent it.
            write_ok = self.backend.write(self.container_id, ret)

            if write_ok:
                print "Successfully collected container {} app metrics..".format(self.container_id)
            else:
                print "Failed to write metrics into backend, pls check backend write log for details."
        except Exception, e:
            import traceback
            print "ERROR while collect container {} app metrics, error: {}\n\n".format(self.container_id, e)
            print traceback.print_exc()
            print "Error exiting current App Metrics Thread for {}".format(self.container_id)

            # just exit, and main-Thread will help me spawn new one.
            self.stop()
            exit(-1)
