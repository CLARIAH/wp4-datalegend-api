FROM python:2.7.13-wheezy

MAINTAINER laurens.rietveld@vu.nl

COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

ENV DATALEGEND_API_APP="/usr/local/datalegend-api"
ENV CONFIG_FILE=${DATALEGEND_API_APP}/src/app/config.py


COPY ./ ${DATALEGEND_API_APP}
RUN cd ${DATALEGEND_API_APP} && git submodule init && git submodule update;
RUN cp ${DATALEGEND_API_APP}/src/app/config_template.py ${CONFIG_FILE}


COPY entrypoint.sh /sbin/entrypoint.sh
RUN chmod 755 /sbin/entrypoint.sh

WORKDIR ${DATALEGEND_API_APP}
ENTRYPOINT ["/sbin/entrypoint.sh"]
CMD ["app:start"]
EXPOSE 5000
