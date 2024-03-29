"""Package configuration details."""

# built-in imports
from setuptools import setup, find_packages

setup(
    name="django_postgres_loader",
    version="0.1.1",
    license="MIT",
    author="Jacob Ayers",
    author_email="jcayers20@gmail.com",
    url="https://github.com/jcayers20/django-postgres-loader",
    download_url="https://github.com/jcayers20/django-postgres-loader/archive/refs/tags/0.1.2.tar.gz",
    packages=find_packages(),
    keywords=["django", "postgres", "PostgreSQL", "ETL", "load"],
    include_package_data=True,
    install_requires=[
        "Django>=2.2.28",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
