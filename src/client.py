# coding=utf-8

import docker
import os
import io
import tarfile
import time


class APIClient(object):
    def __init__(self, configs={}):
        socket = configs["socket"]

        if "tls" in configs:
            is_tls = True

            # config_path = '/etc/pki/CA'
            config_path = configs["tls"]["config_path"]
            cert = os.path.join(config_path, configs["tls"]["cert"])
            key = os.path.join(config_path, configs["tls"]["key"])
            ca = os.path.join(config_path, configs["tls"]["ca"])
        else:
            is_tls = False

        if not is_tls:
            client = docker.Client(base_url=socket)
        else:
            tls_config = docker.tls.TLSConfig(
                client_cert=(cert, key),
                verify=ca,
            )
            client = docker.Client(base_url=socket, tls=tls_config)
        self.client = client
        self.configs = configs

    def containers(self):
        return self.client.containers()

    def execute(self, container_id, cmd, stdout=True, stderr=True,
                tty=False, detach=False, stream=False):
        '''
        run cmd into container, the cmd should be short-simple cmd.
        complex cases should use modules, instead original cmd.
        '''
        exec_id = self.client.exec_create(container_id, cmd,
                                          stdout, stderr, tty)
        ret = self.client.exec_start(exec_id, detach, tty, stream)

        # inspect to check the ret_status, and inject into ret.
        exec_info = self.client.exec_inspect(exec_id)
        return {
            "ret": ret,
            "exitcode": exec_info["ExitCode"]
        }

    def exec_module(self, container_id, module_name):
        # TODO: make a pluggable module executor.
        # Currently, we run the installed modules
        # via `bash <module_dir>/<module_name>`,e.g. `bash /tmp/modules/ss.sh`.
        modules_dst_dir_perfix = self.configs["modules_dst_dir_perfix"]
        exec_module_cmd = "/bin/bash {}{}".format(modules_dst_dir_perfix,
                                                  module_name)
        ret = self.execute(container_id, exec_module_cmd)
        if ret["exitcode"] == 0:
            return {
                "status": "success",
                "data": ret["ret"],
                "message": "successfully run {} module in {}.".format(
                    module_name,
                    container_id,
                )
            }
        else:
            {
                "status": "error",
                "data": "",
                "message": "failed to run {} module in {}, error: {}".format(
                    module_name,
                    container_id,
                    ret["ret"]
                )
            }

    def copy(self, container_id, src, dst,
             is_dir=False, archive_name='files.tgz'):
        def create_archive(artifact_file):
            pw_tarstream = io.BytesIO()
            pw_tar = tarfile.TarFile(fileobj=pw_tarstream, mode='w')
            file_data = open(artifact_file, 'r').read()
            tarinfo = tarfile.TarInfo(name=artifact_file)
            tarinfo.size = len(file_data)
            tarinfo.mtime = time.time()
            # tarinfo.mode = 0600
            pw_tar.addfile(tarinfo, io.BytesIO(file_data))
            pw_tar.close()
            pw_tarstream.seek(0)

            return pw_tarstream

        def create_dir_archive(artifact_dir, archive_name, mode='w:gz'):
            # NOTE: we could also copy archive recursively.
            # but now, we choose tar it and extract it.
            with tarfile.open(archive_name, mode=mode) as archive:
                archive.add(artifact_dir, recursive=True)

            # so, now, the dir is tared as `archive_name`.
            return create_archive(archive_name)

        if is_dir:
            try:
                with create_dir_archive(src, archive_name) as archive:
                    self.client.put_archive(container=container_id,
                                            path=dst, data=archive)
            except Exception as e:
                print "failed to copy {} to {}, error: {}".format(
                    archive_name, dst, e
                )
                return False
            else:
                return True
        else:
            try:
                with create_archive(src) as archive:
                    self.client.put_archive(container=container_id,
                                            path=dst, data=archive)
            except Exception as e:
                print "failed to copy {} to {}, error: {}".format(
                    src, dst, e
                )
                return False
            else:
                return True

    def sync_modules(self, container_id):
        '''
        Do `docker exec` to check whether the fold/files is already exist.
        If not, do `docker cp` to sync modules.

        TODO: maybe `nsenter` would be an alternative or even better.
        '''
        # 1. run docker exec to confirm download is ok.
        # 2. run docker cp if the modules is not synced.
        # 3. finished.
        modules_src_dir = self.configs["modules_src_dir"]
        modules_dst_dir = self.configs["modules_dst_dir"]
        archive_name = "{}-files.tgz".format(container_id)

        # we skip this check process right now, as `sync` operation needs
        # some md5 check.
        # check_modules_cmd = ""
        # has_modules = self.execute(container_id, check_modules_cmd,
        #                            stdout=True, stderr=True)

        # FIXME: the archive sync operation maybe thread unsafe...
        self.copy(container_id, modules_src_dir,
                  modules_dst_dir, is_dir=True, archive_name=archive_name)

        # extract the copied tar files.
        ret = self.execute(container_id, cmd="tar -zxvf {0}{1} -C {0}".format(
            modules_dst_dir, archive_name)
        )
        if ret["exitcode"] == 0:
            print "modules synced..."
            print ret["ret"]
            return True
        else:
            print "modules sync failed..."
            print ret["ret"]
            return False
