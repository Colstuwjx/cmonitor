#!/bin/bash
# <SAMPLE_MODULE>
# filename is the module name right now.
# output data fmt should be prom style.
# (we will translate them into serveral backend via its `write` method.)

# TIPS:
# prom labels could be added via querying ENV Vars.
# NOW, we add sth here as we need them.
# We use the `container_env` perfix, suitable to cadvisor.
LABEL_TASK_ID=`[ -z $TASK_ID ] && echo "" || echo ",container_env_task_id=\"${TASK_ID}\""`
LABEL_APP_ID=`[ -z $APP_ID ] && echo "" || echo ",container_env_app_id=\"${APP_ID}\""`
LABELS="${LABEL_TASK_ID}${LABEL_APP_ID}"

TCP_STATE=`ss -ant |awk '{print $1}' |sort -nr |uniq -c |grep -E -v "State|LISTEN"`
if [ $? != 0 ]; then
    # collect state faced error will exit immediately.
    exit 1
fi

oldIFS=$IFS
IFS=$'\n'
for state in $TCP_STATE
do
    v=`echo $state|awk '{print $1}'`
    k=`echo $state|awk '{print $2}'`

    if [ ! -z ${LABELS} ]; then
        echo "container_tcp_state{state=\"$k\"${LABELS}} $v"
    fi
done
IFS=$oldIFS
