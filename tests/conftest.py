"""Shared fixtures: a Postgres for the persistence tests and the calculator marts from a simulated world.

The Postgres comes from DOORSTEP_TEST_DATABASE_URL when it is set (CI, a developer's own server) and
otherwise from a temporary cluster started with the local binaries for the session, as the postgres
user when the tests run as root; when neither is possible the tests that need it skip by name, and
CI forbids the skip with DOORSTEP_REQUIRE_POSTGRES=1.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

PG_BIN_CANDIDATES = ("/usr/lib/postgresql/16/bin", "/usr/lib/postgresql/15/bin", "/usr/local/pgsql/bin")


def _pg_bin() -> Path | None:
    for candidate in PG_BIN_CANDIDATES:
        if (Path(candidate) / "pg_ctl").exists():
            return Path(candidate)
    found = shutil.which("pg_ctl")
    return Path(found).parent if found else None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _run_as_postgres(command: list[str]) -> subprocess.CompletedProcess[str]:
    if os.geteuid() == 0:
        joined = " ".join(f"'{c}'" for c in command)
        return subprocess.run(
            ["su", "postgres", "-s", "/bin/bash", "-c", joined], capture_output=True, text=True, check=False
        )
    return subprocess.run(command, capture_output=True, text=True, check=False)


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    url = os.environ.get("DOORSTEP_TEST_DATABASE_URL", "").strip()
    if url:
        yield url
        return
    pg_bin = _pg_bin()
    if pg_bin is None:
        from tests._deps import need

        need("postgres", False, "no DOORSTEP_TEST_DATABASE_URL and no local Postgres binaries")
        return
    tmp = Path(tempfile.mkdtemp(prefix="doorstep-pg-", dir="/tmp"))
    os.chmod(tmp, 0o777)
    data = tmp / "data"
    port = _free_port()
    init = _run_as_postgres(
        [str(pg_bin / "initdb"), "-D", str(data), "-A", "trust", "--no-sync", "-U", "postgres"]
    )
    if init.returncode != 0:
        from tests._deps import need

        need("postgres", False, f"initdb failed: {init.stderr[-300:]}")
        return
    start = _run_as_postgres(
        [
            str(pg_bin / "pg_ctl"),
            "-D",
            str(data),
            "-o",
            f"-p {port} -k {tmp} -c fsync=off",
            "-l",
            str(tmp / "log.txt"),
            "-w",
            "start",
        ]
    )
    if start.returncode != 0:
        from tests._deps import need

        need("postgres", False, f"pg_ctl start failed: {start.stderr[-300:]}")
        return
    time.sleep(0.5)
    _run_as_postgres(
        [str(pg_bin / "createdb"), "-p", str(port), "-h", str(tmp), "-U", "postgres", "doorstep_test"]
    )
    try:
        yield f"postgresql+psycopg://postgres@127.0.0.1:{port}/doorstep_test"
    finally:
        _run_as_postgres([str(pg_bin / "pg_ctl"), "-D", str(data), "-m", "immediate", "stop"])
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="session")
def calculator_marts(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The calculator marts written from the demonstration world, as the chapters stage writes them."""
    from doorstep_chapters import calculator
    from doorstep_chapters.panel import from_world
    from doorstep_sim.metros import DEMONSTRATION, generate

    marts = tmp_path_factory.mktemp("marts")
    panel = from_world(generate(DEMONSTRATION, 5))
    calculator.write(panel, marts / "no-derived", marts)
    return marts
