FROM python:2.7
MAINTAINER Colstuwjx <Colstuwjx@gmail.com>

ADD src/ .
COPY supervisord.conf /
RUN pip install -r requirements.txt -i http://pypi.douban.com/simple/ --trusted-host pypi.douban.com

# run supervisord to manage both monitor & http api server processes.
CMD supervisord -n
