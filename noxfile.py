"""Nox sessions."""
import sys

import nox
from nox_poetry import Session, session

package = "result_service_gui"
locations = "result_service_gui", "tests", "noxfile.py"
nox.options.envdir = ".cache"
nox.options.reuse_existing_virtualenvs = True
nox.options.stop_on_first_error = False
nox.options.sessions = (
    "lint",
    "mypy",
    "pytype",
    # "safety",
    "integration_tests",
    "contract_tests",
)


@session(python="3.10")
def integration_tests(session: Session) -> None:
    """Run the integration test suite."""
    args = session.posargs or ["--cov"]
    session.install(".")
    session.install(
        "coverage[toml]",
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "pytest-aiohttp",
        "aioresponses",
        "requests",
    )
    session.run(
        "pytest",
        "-m integration",
        "-rA",
        *args,
        env={},
    )


@session(python="3.10")
def contract_tests(session: Session) -> None:
    """Run the contract test suite."""
    args = session.posargs
    session.install(".")
    session.install(
        "pytest",
        "pytest-docker",
        "pytest_mock",
        "pytest-asyncio",
        "requests",
    )
    session.run(
        "pytest",
        "-m contract",
        "-rA",
        *args,
        env={
            "CONFIG": "test",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "password",
            "EVENTS_HOST_SERVER": "localhost",
            "EVENTS_HOST_PORT": "8080",
            "USERS_HOST_SERVER": "localhost",
            "USERS_HOST_PORT": "8081",
            "JWT_EXP_DELTA_SECONDS": "60",
            "DB_USER": "event-service",
            "DB_PASSWORD": "password",
            "LOGGING_LEVEL": "INFO",
        },
    )


@session
def black(session: Session) -> None:
    """Run black code formatter."""
    args = session.posargs or locations
    session.install("black")
    session.run("black", *args)


@session
def lint(session: Session) -> None:
    """Lint using flake8."""
    args = session.posargs or locations
    session.install(
        "flake8",
        "flake8-annotations",
        "flake8-bandit",
        "flake8-black",
        "flake8-bugbear",
        "flake8-docstrings",
        "flake8-import-order",
        "darglint",
        "flake8-assertive",
        "flake8-eradicate",
    )
    session.run("flake8", *args)


@session
def safety(session: Session) -> None:
    """Scan dependencies for insecure packages."""
    requirements = session.poetry.export_requirements()
    session.install("safety")
    session.run("safety", "check", "--full-report", f"--file={requirements}")


@session
def mypy(session: Session) -> None:
    """Type-check using mypy."""
    args = session.posargs or [
        "--install-types",
        "--non-interactive",
        "result_service_gui",
        "tests",
    ]
    session.install(".")
    session.install("mypy", "pytest")
    session.run("mypy", *args)
    if not session.posargs:
        session.run("mypy", f"--python-executable={sys.executable}", "noxfile.py")


@session
def pytype(session: Session) -> None:
    """Run the static type checker using pytype."""
    args = session.posargs or ["--disable=import-error", *locations]
    session.install("pytype")
    session.run("pytype", *args)


@session
def coverage(session: Session) -> None:
    """Upload coverage data."""
    session.install("coverage[toml]", "codecov")
    session.run("coverage", "xml", "--fail-under=0")
    session.run("codecov", *session.posargs)
