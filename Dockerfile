# syntax = docker/dockerfile:1.4.0

FROM python:3.12.3-alpine as build
ARG PLUGINS="[]"
ARG PLUGIN_NAMES="[]"
WORKDIR /app
ENV PYTHONPATH=/app
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.cargo/bin

ADD https://astral.sh/uv/install.sh /tmp/install-uv.sh
RUN pip install setuptools==77.0.3

RUN --mount=type=cache,target=/var/cache/apk \
    apk --update-cache upgrade && \
    apk add git build-base jq curl && \
    sh /tmp/install-uv.sh && \
    rm /tmp/install-uv.sh

RUN $HOME/.local/bin/uv --no-binary xmlsec,lxml python3-saml
ADD requirements.txt /app/
#RUN --mount=type=cache,target=/root/.cache \
RUN $HOME/.local/bin/uv pip install --system -r requirements.txt;

ADD uber-wrapper.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/uber-wrapper.sh

RUN <<EOF cat >> PLUGINS.json
$PLUGINS
EOF

RUN jq -r '.[] | "git clone --depth 1 --branch \(.branch|@sh) \(.repo|@sh) \(.path|@sh)"' PLUGINS.json > install_plugins.sh && chmod +x install_plugins.sh && ./install_plugins.sh
ENV uber_plugins=$PLUGIN_NAMES

FROM build as test
ADD requirements_test.txt /app/
#RUN --mount=type=cache,target=/root/.cache \
RUN /root/.local/bin/uv pip install --system -r requirements_test.txt
CMD python -m pytest
ADD . /app

FROM build as release
ENTRYPOINT ["/usr/local/bin/uber-wrapper.sh"]
CMD ["uber"]
ADD . /app
