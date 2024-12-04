FROM base_builder AS builder

RUN python -m pip install 'poetry>=1.7.0,<1.8.0'

RUN mkdir --parents /opt/app
COPY --from=sources pyproject.toml /opt/app/pyproject.toml
COPY --from=sources poetry.lock /opt/app/poetry.lock
COPY --from=sources poetry.toml /opt/app/poetry.toml

WORKDIR /opt/app
RUN poetry install

FROM base_runtime AS runtime

RUN mkdir --parents /opt/app
COPY --from=builder /opt/app/.venv /opt/app/.venv
COPY --from=sources bin /opt/app/bin
COPY --from=sources lib /opt/app/lib

WORKDIR /opt/app
CMD [".venv/bin/python", "-m", "bin.main"]

FROM builder AS builder_dev

RUN poetry install --with dev

FROM base_runtime AS runtime_dev

RUN mkdir --parents /opt/app
COPY --from=builder_dev /opt/app/.venv /opt/app/.venv
COPY --from=sources bin /opt/app/bin
COPY --from=sources lib /opt/app/lib
COPY --from=sources pyproject.toml /opt/app/pyproject.toml

WORKDIR /opt/app

FROM runtime_dev AS tests

COPY --from=sources tests /opt/app/tests

CMD [".venv/bin/python", "-m", "pytest", "tests"]
