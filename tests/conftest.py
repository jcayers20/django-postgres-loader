"""pytest configuration and fixtures for the test suite.

Django is configured here without pytest-django, using the standard
pytest ``pytest_configure`` hook and Django's ``django.setup()`` call.
"""

import io
import os

import django
import pytest
from django.db import connection


def pytest_configure(config):
    """Configure Django settings before any tests are collected."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    django.setup()


@pytest.fixture(scope="session", autouse=True)
def django_db_setup():
    """Create all test model tables before the session and drop them after.

    Uses Django's SchemaEditor to create and destroy tables, so the
    schema exactly matches what Django would generate for each model.
    """
    from tests.models import (
        NaturalKeyModel,
        NullableFieldModel,
        RelatedModel,
        SimpleModel,
        UpsertModel,
    )

    models_to_create = [
        SimpleModel,
        NullableFieldModel,
        NaturalKeyModel,
        UpsertModel,
        RelatedModel,
    ]

    with connection.schema_editor() as editor:
        for model in models_to_create:
            editor.create_model(model)

    yield

    with connection.schema_editor() as editor:
        for model in reversed(models_to_create):
            editor.delete_model(model)


@pytest.fixture(autouse=True)
def clean_tables():
    """Truncate all test tables after each test to ensure isolation."""
    yield

    # Clean up after each test
    with connection.cursor() as cursor:
        cursor.execute(
            'TRUNCATE TABLE "tests_simplemodel", "tests_nullablefieldmodel", '
            '"tests_naturalkeymodel", "tests_upsertmodel", "tests_relatedmodel" '
            "RESTART IDENTITY CASCADE",
        )


# ---------------------------------------------------------------------------
# Data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_csv_stringio():
    """Return CSV StringIO data for SimpleModel."""
    return io.StringIO("name,value\nAlice,1\nBob,2\n")


@pytest.fixture
def simple_csv_path(tmp_path):
    """pathlib.Path to a temporary CSV file for SimpleModel."""
    p = tmp_path / "simple.csv"
    p.write_text("name,value\nAlice,1\nBob,2\n")
    return p


@pytest.fixture
def simple_csv_dataframe(simple_csv_stringio):
    """pandas.DataFrame for SimpleModel; skipped if pandas is not installed."""
    pd = pytest.importorskip("pandas")
    simple_csv_stringio.seek(0)
    return pd.read_csv(simple_csv_stringio)


@pytest.fixture
def upsert_csv_stringio():
    """Provide initial data for UpsertModel."""
    return io.StringIO("identifier,payload\nA,first\nB,second\n")


@pytest.fixture
def upsert_csv_updated_stringio():
    """Provide updated data for UpsertModel (A updated, C inserted)."""
    return io.StringIO("identifier,payload\nA,updated\nC,third\n")


@pytest.fixture
def natural_key_csv_stringio():
    """CSV data for NaturalKeyModel."""
    return io.StringIO("code,label\nX,Ex\nY,Why\n")


@pytest.fixture
def nullable_csv_stringio():
    """Minimal CSV for NullableFieldModel (only required fields)."""
    return io.StringIO("name\nRequired\n")
