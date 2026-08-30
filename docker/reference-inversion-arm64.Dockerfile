FROM python:3.11.11-slim-bookworm

ARG ETAS_REPOSITORY=https://github.com/ss15859/etas.git
ARG ETAS_COMMIT=51e0c8e419197df3f88349035a682b90fbd4dfb5
ARG SEISMOSTATS_REPOSITORY=https://github.com/swiss-seismological-service/SeismoStats.git
ARG SEISMOSTATS_COMMIT=4d617d6b54a57898f9ccae56ea24f4a071924dc3

# Cartopy 0.22 has no CPython 3.11 aarch64 wheel and must compile its extension.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git g++ \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
    certifi==2025.1.31 \
    cartopy==0.22.0 \
    charset-normalizer==3.3.2 \
    contourpy==1.3.1 \
    cycler==0.11.0 \
    fonttools==4.55.3 \
    idna==3.7 \
    jinja2==3.1.5 \
    kiwisolver==1.4.8 \
    markupsafe==3.0.2 \
    matplotlib==3.10.0 \
    numpy==1.26.4 \
    packaging==24.2 \
    pandas==2.2.3 \
    pillow==11.1.0 \
    pyproj==3.6.1 \
    pynverse==0.1.4.6 \
    pyparsing==3.2.0 \
    pyshp==2.3.1 \
    requests==2.32.3 \
    scipy==1.15.1 \
    shapely==2.0.6 \
    tabulate==0.9.0 \
    urllib3==2.3.0 \
    joblib==1.4.2

RUN python -m pip install --no-cache-dir --no-deps geopandas==0.14.4
RUN python -m pip install --no-cache-dir --no-deps \
    "git+${SEISMOSTATS_REPOSITORY}@${SEISMOSTATS_COMMIT}"
RUN python -m pip install --no-cache-dir --no-deps --ignore-requires-python \
    "git+${ETAS_REPOSITORY}@${ETAS_COMMIT}"

WORKDIR /workspace
ENV PYTHONPATH=/workspace/src
