"""Package configuration details."""

# built-in imports
from setuptools import setup, find_packages

setup(
    name="django_postgres_loader",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[
        "Django>=2.2.28",
    ],
)
