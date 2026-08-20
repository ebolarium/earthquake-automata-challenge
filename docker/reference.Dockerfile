FROM python:3.11.11-slim-bookworm

ARG ETAS_REPOSITORY=https://github.com/ss15859/etas.git
ARG ETAS_COMMIT=51e0c8e419197df3f88349035a682b90fbd4dfb5
ARG SEISMOSTATS_REPOSITORY=https://github.com/swiss-seismological-service/SeismoStats.git
ARG SEISMOSTATS_COMMIT=4d617d6b54a57898f9ccae56ea24f4a071924dc3

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
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
    urllib3==2.3.0

# Fiona is an optional GeoPandas file-I/O backend. ETAS uses in-memory geometry
# operations, so GeoPandas is installed without the unused GDAL/Fiona stack.
RUN python -m pip install --no-cache-dir --no-deps geopandas==0.14.4
RUN python -m pip install --no-cache-dir joblib==1.4.2

# EarthquakeNPP declares pyCSEP 0.6.3 but its ETAS image did not install the
# evaluation stack. Pin the complete resolved stack used by this project.
RUN python -m pip install --no-cache-dir \
    click==8.4.2 \
    decorator==5.3.1 \
    greenlet==3.5.5 \
    lxml==6.1.2 \
    mercantile==1.2.1 \
    obspy==1.5.0 \
    python-dateutil==2.9.0.post0 \
    pytz==2026.3.post1 \
    six==1.17.0 \
    sqlalchemy==2.0.52 \
    typing-extensions==4.16.0 \
    tzdata==2026.3 \
    pycsep==0.6.3

# This dependency is imported by etas.evaluation but omitted from the ETAS
# package metadata. Pin the exact commit recorded by the historical ETAS
# requirements file. Its optional map/file backends are not used here.
RUN python -m pip install --no-cache-dir --no-deps \
    "git+${SEISMOSTATS_REPOSITORY}@${SEISMOSTATS_COMMIT}"

# EarthquakeNPP records Python 3.11.11, while this historical ETAS commit
# declares Python >=3.12 in package metadata. The benchmark nevertheless used
# the fork from a Python 3.11 environment, so only that metadata guard is
# bypassed here. All runtime dependencies remain explicitly pinned above.
RUN python -m pip install --no-cache-dir --no-deps --ignore-requires-python \
    "git+${ETAS_REPOSITORY}@${ETAS_COMMIT}"

WORKDIR /workspace
ENV PYTHONPATH=/workspace/src

CMD ["python", "scripts/reference_environment.py"]
