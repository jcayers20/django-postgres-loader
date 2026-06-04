"""Tests for the CopyLoader pipeline via CopyManager.load()."""

import builtins
import io
import logging
import uuid
from unittest.mock import patch

import pytest
from django.db import connection

from tests.models import (
    NaturalKeyModel,
    NullableFieldModel,
    SimpleModel,
    UpsertModel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data source type tests
# ---------------------------------------------------------------------------


class TestDataSources:
    """load() accepts StringIO, Path, and DataFrame; rejects str."""

    def test_stringio(self, simple_csv_stringio):
        """Load rows from an in-memory StringIO source."""
        count = SimpleModel.objects.load(
            data=simple_csv_stringio,
            method="append",
        )
        assert count == 2
        assert SimpleModel.objects.count() == 2

    def test_path(self, simple_csv_path):
        """Load rows from a pathlib.Path source."""
        count = SimpleModel.objects.load(data=simple_csv_path, method="append")
        assert count == 2
        assert SimpleModel.objects.count() == 2

    def test_dataframe(self, simple_csv_dataframe):
        """Load rows from a pandas DataFrame source."""
        count = SimpleModel.objects.load(
            data=simple_csv_dataframe,
            method="append",
        )
        assert count == 2
        assert SimpleModel.objects.count() == 2

    def test_bare_str_raises_type_error(self):
        """Reject bare string paths and require supported data source types."""
        with pytest.raises(TypeError, match=r"io\.StringIO"):
            SimpleModel.objects.load(
                data="name,value\nAlice,1\n",
                method="append",
            )


# ---------------------------------------------------------------------------
# Method: append
# ---------------------------------------------------------------------------


class TestAppend:
    """append inserts all rows unconditionally."""

    def test_append_inserts_rows(self, simple_csv_stringio):
        """Insert all CSV rows with append."""
        SimpleModel.objects.load(data=simple_csv_stringio, method="append")
        assert SimpleModel.objects.count() == 2

    def test_append_is_additive(self, simple_csv_stringio):
        """Append rows cumulatively across multiple loads."""
        SimpleModel.objects.load(data=simple_csv_stringio, method="append")
        simple_csv_stringio.seek(0)
        SimpleModel.objects.load(data=simple_csv_stringio, method="append")
        assert SimpleModel.objects.count() == 4


# ---------------------------------------------------------------------------
# Method: replace
# ---------------------------------------------------------------------------


class TestReplace:
    """replace deletes all existing rows then inserts from CSV."""

    def test_replace_inserts_rows(self, simple_csv_stringio):
        """Insert CSV rows into an empty table with replace."""
        count = SimpleModel.objects.load(
            data=simple_csv_stringio,
            method="replace",
        )
        assert count == 2
        assert SimpleModel.objects.count() == 2

    def test_replace_overwrites_existing(self, simple_csv_stringio):
        """Overwrite existing rows when replace is used."""
        SimpleModel.objects.load(data=simple_csv_stringio, method="append")
        new_data = io.StringIO("name,value\nCharlie,3\n")
        count = SimpleModel.objects.load(data=new_data, method="replace")
        assert count == 1
        assert SimpleModel.objects.count() == 1
        assert SimpleModel.objects.first().name == "Charlie"


# ---------------------------------------------------------------------------
# Method: update
# ---------------------------------------------------------------------------


class TestUpdate:
    """update merges matching rows; unmatched source rows are discarded."""

    def test_update_matched_rows(
        self,
        upsert_csv_stringio,
        upsert_csv_updated_stringio,
    ):
        """Update only matching target rows when join keys match."""
        UpsertModel.objects.load(data=upsert_csv_stringio, method="append")
        UpsertModel.objects.load(
            data=upsert_csv_updated_stringio,
            method="update",
            join_columns=["identifier"],
        )
        # A should be updated; B unchanged; C not inserted
        assert UpsertModel.objects.count() == 2
        assert UpsertModel.objects.get(identifier="A").payload == "updated"
        assert UpsertModel.objects.get(identifier="B").payload == "second"
        assert not UpsertModel.objects.filter(identifier="C").exists()

    def test_update_requires_join_columns(self, upsert_csv_stringio):
        """Require join_columns when using update."""
        with pytest.raises(ValueError, match="join_columns"):
            UpsertModel.objects.load(data=upsert_csv_stringio, method="update")


# ---------------------------------------------------------------------------
# Method: upsert
# ---------------------------------------------------------------------------


class TestUpsert:
    """upsert updates matched rows and inserts unmatched rows."""

    def test_upsert_updates_and_inserts(
        self,
        upsert_csv_stringio,
        upsert_csv_updated_stringio,
    ):
        """Update matched rows and insert unmatched rows during upsert."""
        UpsertModel.objects.load(data=upsert_csv_stringio, method="append")
        UpsertModel.objects.load(
            data=upsert_csv_updated_stringio,
            method="upsert",
            join_columns=["identifier"],
        )
        assert UpsertModel.objects.count() == 3
        assert UpsertModel.objects.get(identifier="A").payload == "updated"
        assert UpsertModel.objects.get(identifier="B").payload == "second"
        assert UpsertModel.objects.get(identifier="C").payload == "third"

    def test_upsert_requires_join_columns(self, upsert_csv_stringio):
        """Require join_columns when using upsert."""
        with pytest.raises(ValueError, match="join_columns"):
            UpsertModel.objects.load(data=upsert_csv_stringio, method="upsert")


# ---------------------------------------------------------------------------
# Nullable fields
# ---------------------------------------------------------------------------


class TestNullableFields:
    """Behavior tests for nullable model fields during load."""

    def test_nullable_field_not_required_in_csv(self, nullable_csv_stringio):
        """A non-required nullable field need not appear in the CSV."""
        count = NullableFieldModel.objects.load(
            data=nullable_csv_stringio,
            method="append",
        )
        assert count == 1


# ---------------------------------------------------------------------------
# Natural key model
# ---------------------------------------------------------------------------


class TestNaturalKeyModel:
    """Behavior tests for loading models with natural primary keys."""

    def test_natural_key_load(self, natural_key_csv_stringio):
        """Load rows into a model that uses a non-auto primary key."""
        count = NaturalKeyModel.objects.load(
            data=natural_key_csv_stringio,
            method="append",
        )
        assert count == 2
        assert NaturalKeyModel.objects.count() == 2


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidation:
    """Parameter validation raises appropriate errors."""

    def test_invalid_method_raises(self, simple_csv_stringio):
        """Raise ValueError for unsupported method names."""
        with pytest.raises(ValueError, match="method"):
            SimpleModel.objects.load(data=simple_csv_stringio, method="invalid")

    def test_unknown_csv_column_raises(self):
        """Raise ValueError when CSV includes an unknown column."""
        bad_data = io.StringIO("name,value,unknown_field\nAlice,1,extra\n")
        with pytest.raises(ValueError, match="unknown_field"):
            SimpleModel.objects.load(data=bad_data, method="append")

    def test_invalid_delimiter_raises(self, simple_csv_stringio):
        """Raise ValueError for invalid delimiter values."""
        with pytest.raises(ValueError, match="delimiter"):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                delimiter="too_long",
            )

    def test_invalid_temp_table_name_raises(self, simple_csv_stringio):
        """Raise ValueError for invalid temporary table names."""
        with pytest.raises(ValueError, match="temp_table_name"):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                temp_table_name="123invalid",
            )

    def test_invalid_encoding_raises(self, simple_csv_stringio):
        """Raise ValueError for invalid encoding strings."""
        with pytest.raises(ValueError, match="encoding"):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                encoding="utf 8",
            )


class TestKeepTempTable:
    """Tests for the keep_temp_table parameter."""

    def test_temp_table_is_kept_if_true(self, simple_csv_stringio):
        """Ensure temp table exists when keep_temp_table=True."""
        temp_table_name = f"tmp_keep_temp_{uuid.uuid4().hex[:8]}"
        SimpleModel.objects.load(
            data=simple_csv_stringio,
            method="append",
            temp_table_name=temp_table_name,
            keep_temp_table=True,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT name, value FROM pg_temp."{temp_table_name}" ORDER BY name',
            )
            rows = cursor.fetchall()

        # Log the rows so the temp table contents are visible in test output.
        logger.info("temp table %s rows: %s", temp_table_name, rows)

        assert rows == [("Alice", 1), ("Bob", 2)]

    def test_temp_table_is_dropped_if_false(self, simple_csv_stringio):
        """Ensure temp table is dropped when keep_temp_table=False."""
        temp_table_name = f"tmp_drop_temp_{uuid.uuid4().hex[:8]}"
        SimpleModel.objects.load(
            data=simple_csv_stringio,
            method="append",
            temp_table_name=temp_table_name,
            keep_temp_table=False,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname = %s AND n.nspname LIKE 'pg_temp_%%'"
                ")",
                [temp_table_name],
            )
            exists = cursor.fetchone()[0]

        assert not exists

    def test_temp_table_is_dropped_by_default(self, simple_csv_stringio):
        """Ensure temp table is dropped when keep_temp_table is not set."""
        temp_table_name = f"tmp_default_drop_{uuid.uuid4().hex[:8]}"
        SimpleModel.objects.load(
            data=simple_csv_stringio,
            method="append",
            temp_table_name=temp_table_name,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname = %s AND n.nspname LIKE 'pg_temp_%%'"
                ")",
                [temp_table_name],
            )
            exists = cursor.fetchone()[0]

        assert not exists


class TestDataSourceValidation:
    """Validation tests for supported and unsupported data sources."""

    def test_nonexistent_path_raises(self, tmp_path):
        """Raise ValueError when a pathlib.Path does not exist."""
        nonexistent_path = tmp_path / "nonexistent.csv"
        with pytest.raises(ValueError, match="does not exist"):
            SimpleModel.objects.load(data=nonexistent_path, method="append")

    def test_unparseable_file_raises(self, tmp_path):
        """Raise ValueError when file bytes cannot be parsed as CSV."""
        bad_path = tmp_path / "bad.csv"
        bad_path.write_bytes(b"name,value\nnul\x00byte,1\n")
        with pytest.raises(ValueError, match="cannot be parsed as CSV"):
            SimpleModel.objects.load(data=bad_path, method="append")

    def test_non_pandas_non_supported_type_raises_when_pandas_mocked_absent(
        self,
    ):
        """Raise TypeError for unsupported data types if pandas unavailable."""
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(TypeError, match=r"io\.StringIO"):
                SimpleModel.objects.load(data={"key": "value"}, method="append")


class TestColumnValidation:
    """Validation tests for required CSV columns."""

    def test_missing_required_column_raises(self):
        """Raise ValueError when a required non-nullable column is missing."""
        data = io.StringIO("name\nAlice\n")
        with pytest.raises(ValueError, match=r"non-nullable|value"):
            SimpleModel.objects.load(data=data, method="append")


class TestJoinColumnValidation:
    """Validation and warning behavior for join_columns."""

    def test_join_columns_ignored_warning_for_append(
        self,
        caplog,
        simple_csv_stringio,
    ):
        """Log a warning when join_columns is passed to append."""
        with caplog.at_level(
            logging.WARNING,
            logger="django_postgres_loader.load",
        ):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                join_columns=["name"],
            )
        assert "join_columns is ignored" in caplog.text

    def test_join_columns_ignored_warning_for_replace(
        self,
        caplog,
        simple_csv_stringio,
    ):
        """Log a warning when join_columns is passed to replace."""
        with caplog.at_level(
            logging.WARNING,
            logger="django_postgres_loader.load",
        ):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="replace",
                join_columns=["name"],
            )
        assert "join_columns is ignored" in caplog.text

    def test_unknown_join_column_raises(self, upsert_csv_stringio):
        """Raise ValueError when a join column is not a model field."""
        with pytest.raises(ValueError, match=r"nonexistent_col|join_columns"):
            UpsertModel.objects.load(
                data=upsert_csv_stringio,
                method="upsert",
                join_columns=["nonexistent_col"],
            )


class TestCopyParameterValidation:
    """Validation tests for COPY-related parameters."""

    def test_non_string_delimiter_raises(self, simple_csv_stringio):
        """Raise ValueError when delimiter is not a string."""
        with pytest.raises(ValueError, match="delimiter"):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                delimiter=99,
            )

    def test_non_string_null_string_raises(self, simple_csv_stringio):
        """Raise ValueError when null_string is not a string."""
        with pytest.raises(ValueError, match="null_string"):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                null_string=42,
            )

    def test_non_string_quote_character_raises(self, simple_csv_stringio):
        """Raise ValueError when quote_character is not a string."""
        with pytest.raises(ValueError, match="quote_character"):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                quote_character=42,
            )

    def test_multi_char_quote_character_raises(self, simple_csv_stringio):
        """Raise ValueError when quote_character has more than one character."""
        with pytest.raises(ValueError, match="quote_character"):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                quote_character="too_long",
            )

    def test_empty_quote_character_raises(self, simple_csv_stringio):
        """Raise ValueError when quote_character is empty."""
        with pytest.raises(ValueError, match="quote_character"):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                quote_character="",
            )

    def test_unknown_force_not_null_column_raises(self, simple_csv_stringio):
        """Raise ValueError for unknown columns in force_not_null."""
        with pytest.raises(
            ValueError,
            match=r"nonexistent_field|force_not_null",
        ):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                force_not_null=["nonexistent_field"],
            )

    def test_unknown_force_null_column_raises(self, simple_csv_stringio):
        """Raise ValueError for unknown columns in force_null."""
        with pytest.raises(ValueError, match=r"nonexistent_field|force_null"):
            SimpleModel.objects.load(
                data=simple_csv_stringio,
                method="append",
                force_null=["nonexistent_field"],
            )
