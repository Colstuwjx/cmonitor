# CMonitor
Another container hacky monitor for sth cadvisor could not covered.
CMonitor is designed for some missing metrics to cadvisor, such as process level
metrics and tcp states etc.

## design
CMonitor is dead simple and just:

* use `docker cp` to sync modules(now, they are shells);
* use `docker exec` to execute them and collect metrics. 

## limitation
CMonitor uses `docker exec`, `docker cp` to collect metrics,
it's really unsafe and not predictable...

## build

```
git clone git@github.com:Colstuwjx/cmonitor.git
cd cmonitor
docker build -t cmonitor:0.1 .
```

## ship

```
docker push cmonitor:0.1
```

## prepare configs

```
cp src/config/config.yml /opt/cmonitor-config.yml
```

## run

```
# no TLS
docker run -itd \
    --net host \
    --restart always \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /opt/cmonitor-config.yml:/config/config.yml \
    -e CONFIG_PATH=/config/config.yml \
    --name cmonitor \
    cmonitor:0.1
```

```
# with TLS, you need write TLS configs into cmonitor-config.yml
docker run -itd \
    --net host \
    --restart always \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /opt/cmonitor-config.yml:/config/config.yml \
    -v /etc/pki/CA/:/etc/pki/CA/ \
    -e CONFIG_PATH=/config/config.yml \
    --name cmonitor \
    cmonitor:0.1
```