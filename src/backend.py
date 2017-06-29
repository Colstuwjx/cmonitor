# coding=utf-8
import os
import glob
from client import APIClient
import re


class Backend(object):
    def __init__(self, configs):
        # TODO: make a cache backend to serve the data,
        # rather than using the prom textfile metrics.
        self.configs = configs

    def write(self, data):
        '''
        save the collected data into the backend.
        '''
        return True

    def read(self):
        '''
        return the data stored in backend,
        now it returns the full data.
        '''
        return None


class PromCache(Backend):
    '''
    Storage backend for CMonitor.
    Now, it would be a local cache, and
    served for Prometheus.
    '''
    def __init__(self, configs):
        super(PromCache, self).__init__(configs)

    def write(self, container_id, data):
        '''
        save `data` into specified dir for node-exporter consuming.
        '''
        data_dir = self.configs["backend"]["data_dir"]
        data_perfix = self.configs["backend"]["data_perfix"]
        if isinstance(data, dict):
            for mod, mod_metrics in data.iteritems():
                mod_writing_textfile = data_dir + data_perfix + container_id \
                    + "_" + mod + ".prom.$$"
                mod_textfile = data_dir + data_perfix + container_id \
                    + "_" + mod + ".prom"

                if not mod_metrics or "data" not in mod_metrics or \
                   not mod_metrics["data"]:
                    # the metrics is invalid, fail it!
                    continue
                else:
                    # FIXME: thread is unsafe!!!
                    with open(mod_writing_textfile, 'w') as fp:
                        fp.write(mod_metrics["data"])
                    os.rename(mod_writing_textfile, mod_textfile)
            return True
        else:
            print "invalid data: {} from {}".format(data, container_id)
            return False

    def read(self):
        data_dir = self.configs["backend"]["data_dir"]
        registered_modules = self.configs["registered_modules"]
        prom_textfile_style = self.configs["backend"]["prom_textfile_style"]
        prom_textfile_regex = self.configs["backend"]["prom_textfile_regex"]
        prom_textfiles = glob.glob(data_dir + prom_textfile_style)

        metrics = {}
        reg = re.compile(prom_textfile_regex)
        for metric_file in prom_textfiles:
            # FIXME: maybe unsafe here!!!
            # NOTE: read must divide into multiple modules,
            # and add HEADER for them.
            matched = reg.search(metric_file)
            container_id, mod_name = matched.groups()

            # each containers' same mod metric should be
            # merged with annotation header.
            each_metric = open(metric_file, 'r').read()
            if mod_name not in metrics:
                mod_annotation = registered_modules[mod_name]["annotation"]
                metrics[mod_name] = mod_annotation + each_metric
            else:
                metrics[mod_name] += each_metric
        return metrics

    @classmethod
    def housekeeping(cls, configs={}):
        '''
        another background process, clean up the out-of-date textfile metrics.
        we assumed that there is ONLY 1 layer files under the `data_dir`.
        '''
        data_dir = configs["backend"]["data_dir"]
        prom_textfile_style = configs["backend"]["prom_textfile_style"]
        prom_textfiles = glob.glob(data_dir + prom_textfile_style)
        client = APIClient(configs)

        current_container_ids = [cnter["Id"] for cnter in client.containers()]
        for metric_file in prom_textfiles:
            has_metric = False
            for container_id in current_container_ids:
                if container_id in metric_file:
                    has_metric = True
                    break
                else:
                    continue

            if not has_metric:
                # clean up the out-of-date metric!
                os.remove(metric_file)
                print "Cleaned out-of-date metric file: {}".format(metric_file)


def BackendFactory(backend):
    backends = {
        "PromCache": PromCache
    }
    return backends.get(backend)
