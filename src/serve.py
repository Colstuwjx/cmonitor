# coding=utf-8

'''
CMonitor HTTP API serves the `/metrics` API
make its backend metrics exposed and available on the endpoint!
'''

from flask import Flask
from flask import Response
import os
import yaml
from backend import BackendFactory
app = Flask(__name__)

# load configs.
# TODO: make it as a startup parameter.
configs = {}
config_file = os.getenv('CONFIG', 'config/config.yml')
with open(config_file, 'r') as fp:
    configs = yaml.load(fp)
app.configs = configs


@app.route("/")
def index():
    return "Hello World!"


@app.route("/metrics")
def metrics():
    # initial the configs & backend.
    # read metrics from backend & expose it!
    from flask import current_app
    if hasattr(current_app, "configs"):
        configs = current_app.configs
    else:
        configs = {}

    backend = BackendFactory(configs["backend"]["name"])(
        configs=configs
    )
    data = backend.read()
    ret = ""
    for mod, mod_metrics in data.items():
        ret += mod_metrics

    resp = Response(ret)
    resp.headers['Content-Type'] = 'text/plain'
    return resp


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9118)
