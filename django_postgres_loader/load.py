"""Core loading pipeline: create temp table, COPY, merge, drop."""

import csv
import io
import logging
import random
import re
import string
from pathlib import Path
from typing import Any, TypeAlias

from django.db import connection, models, transaction
from django.db.backends.utils import CursorWrapper

from .core.definitions import VALID_METHODS, render_template

logger = logging.getLogger(__name__)

# Regex for valid PostgreSQL identifiers (temp table names)
_TEMP_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")

# Minimum supported PostgreSQL major version (MERGE requires 15+)
_MIN_PG_MAJOR_VERSION = 15

CopyDataSource: TypeAlias = io.StringIO | Path | Any


class CopyLoader:
    """Implements the four-step CSV loading pipeline for a PostgreSQL table.

    The pipeline:
        1. Create a temporary table with the same columns as the target model.
        2. COPY CSV data into the temp table via COPY ... FROM STDIN.
        3. Merge rows from the temp table into the target model table using
           the SQL strategy that matches ``method``.
        4. Drop the temp table (skipped when ``keep_temp_table=True``).

    The entire pipeline runs inside ``transaction.atomic()``. The DROP step
    is wrapped in ``try/finally`` so it executes even if an earlier step
    raises an exception.
    """

    def __init__(
        self,
        model: type[models.Model],
        data: CopyDataSource,
        method: str,
        join_columns: list[str] | None = None,
        delimiter: str | None = None,
        null_string: str | None = None,
        quote_character: str | None = None,
        force_not_null: list[str] | None = None,
        force_null: list[str] | None = None,
        encoding: str | None = None,
        temp_table_name: str | None = None,
        keep_temp_table: bool = False,
    ) -> None:
        """Initialise and validate all parameters.

        Args:
            model: The Django model class whose table will receive the data.
            data: Data source — ``io.StringIO``, ``pathlib.Path``, or a
                ``pandas.DataFrame``.
            method: One of ``"replace"``, ``"append"``, ``"update"``,
                ``"upsert"``.
            join_columns: Columns used to match rows. Required for
                ``"update"``/``"upsert"``; ignored for the others.
            delimiter: Single-character CSV delimiter.
            null_string: String representing NULL in the CSV.
            quote_character: Single-character CSV quote character.
            force_not_null: Columns for ``FORCE_NOT_NULL`` in COPY.
            force_null: Columns for ``FORCE_NULL`` in COPY.
            encoding: File encoding for the COPY operation.
            temp_table_name: Custom temp table name; auto-generated if omitted.
            keep_temp_table: Skip the DROP step when ``True``.
        """
        self.model = model
        self.keep_temp_table = keep_temp_table

        # Discover model metadata before any further validation
        self._model_field_names: set[str] = self._get_model_field_names()
        self._auto_field_names: set[str] = self._get_model_auto_field_names()

        # Normalise data into a StringIO before reading column headers
        self.data: io.StringIO = self._normalize_data(data)

        self._validate_delimiter(delimiter)
        self.delimiter = delimiter

        # Read CSV column headers from the normalised data
        self.data_columns: list[str] = self._get_data_columns()

        # Validate CSV columns against the model allow-list
        self._validate_data_columns()

        # Validate and store all other parameters
        self._validate_method(method)
        self.method = method

        self._validate_join_columns(join_columns)
        self.join_columns = join_columns

        self._validate_null_string(null_string)
        self.null_string = null_string

        self._validate_quote_character(quote_character)
        self.quote_character = quote_character

        self._validate_column_list(force_not_null, "force_not_null")
        self.force_not_null = force_not_null

        self._validate_column_list(force_null, "force_null")
        self.force_null = force_null

        self._validate_encoding(encoding)
        self.encoding = encoding

        if temp_table_name is None:
            self.temp_table_name: str = self._generate_temp_table_name()
        else:
            self._validate_temp_table_name(temp_table_name)
            self.temp_table_name = temp_table_name

    # --------------------------------------------------------------------------
    # Data normalization
    # --------------------------------------------------------------------------

    def _normalize_data(self, data: CopyDataSource) -> io.StringIO:
        """Convert *data* to an ``io.StringIO`` instance.

        Accepted types:
            - ``io.StringIO`` — rewound to position 0 and returned as-is.
            - ``pathlib.Path`` — file is read, content is validated as CSV,
              and wrapped in ``StringIO``.
            - ``pandas.DataFrame`` — converted via ``to_csv(index=False)``
              and wrapped in ``StringIO``.

        Raises:
            TypeError: For any other type, including bare ``str``.
            ValueError: If a ``Path`` does not exist, is not readable, or
                the file content cannot be parsed as CSV.
        """
        if isinstance(data, io.StringIO):
            data.seek(0)
            return data

        if isinstance(data, Path):
            if not data.is_file():
                raise ValueError(
                    f"File does not exist or is not readable: {data}",
                )
            content = data.read_text()
            # Validate that the content can be parsed as CSV
            try:
                reader = csv.reader(io.StringIO(content))
                list(reader)  # read all rows to surface parse errors
            except csv.Error as exc:
                raise ValueError(
                    f"File cannot be parsed as CSV: {exc}",
                ) from exc
            return io.StringIO(content)

        # Detect pandas DataFrame without importing pandas at module level
        try:
            import pandas as pd  # noqa: PLC0415

            if isinstance(data, pd.DataFrame):
                return io.StringIO(data.to_csv(index=False))
        except ImportError:
            pass  # pandas not installed — fall through to TypeError

        raise TypeError(
            "data must be io.StringIO, pathlib.Path, or pandas DataFrame. "
            f"Got: {type(data).__name__}",
        )

    # --------------------------------------------------------------------------
    # Model metadata helpers
    # --------------------------------------------------------------------------

    def _get_model_field_names(self) -> set[str]:
        """Return the set of database column names defined on the model."""
        return {f.column for f in self.model._meta.get_fields() if hasattr(f, "column")}

    def _get_model_auto_field_names(self) -> set[str]:
        """Return the set of auto-increment field column names."""
        return {
            f.column
            for f in self.model._meta.get_fields()
            if isinstance(
                f,
                (models.AutoField, models.BigAutoField, models.SmallAutoField),
            )
        }

    # --------------------------------------------------------------------------
    # Data column helpers
    # --------------------------------------------------------------------------

    def _get_data_columns(self) -> list[str]:
        """Read and return the CSV header row column names."""
        self.data.seek(0)
        delimiter = self.delimiter or ","
        reader = csv.reader(self.data, delimiter=delimiter)
        columns = next(reader)
        self.data.seek(0)
        return columns

    def _validate_data_columns(self) -> None:
        """Validate CSV columns against the model's field allow-list.

        Raises:
            ValueError: If any CSV column is not a model field, or if any
                required (non-nullable, non-auto) model field is absent.
        """
        # Every CSV column must map to a known model field
        for col in self.data_columns:
            if col not in self._model_field_names:
                raise ValueError(
                    f"CSV column '{col}' does not correspond to any field on "
                    f"{self.model.__name__}. Valid fields: "
                    f"{sorted(self._model_field_names)}",
                )

        # Every non-nullable, non-auto field must be present in the CSV
        csv_col_set = set(self.data_columns)
        for field in self.model._meta.get_fields():
            if not hasattr(field, "column"):
                continue
            if field.column in self._auto_field_names:
                continue  # auto fields are exempt
            if (
                hasattr(field, "null")
                and not field.null
                and not field.primary_key
                and field.column not in csv_col_set
            ):
                raise ValueError(
                    f"Required field '{field.column}' on "
                    f"{self.model.__name__} is non-nullable but was not "
                    "found in the CSV data.",
                )

    # --------------------------------------------------------------------------
    # Parameter validation
    # --------------------------------------------------------------------------

    def _validate_method(self, method: str) -> None:
        """Validate that *method* is a supported insertion method."""
        if method not in VALID_METHODS:
            raise ValueError(
                f"method must be one of {VALID_METHODS}. Got: {method!r}",
            )

    def _validate_join_columns(self, join_columns: list[str] | None) -> None:
        """Validate *join_columns* against the method and the model's fields.

        Raises:
            ValueError: If join_columns is required but absent, or if any
                column name is not a model field.
        """
        if self.method in ("update", "upsert"):
            if not join_columns:
                raise ValueError(
                    f"join_columns is required when method is '{self.method}'.",
                )
        elif join_columns is not None:
            logger.warning(
                "join_columns is ignored for method '%s'.",
                self.method,
            )

        if join_columns is not None:
            for col in join_columns:
                if col not in self._model_field_names:
                    raise ValueError(
                        f"join_columns value '{col}' is not a field on "
                        f"{self.model.__name__}. Valid fields: "
                        f"{sorted(self._model_field_names)}",
                    )

    def _validate_delimiter(self, delimiter: str | None) -> None:
        """Validate that *delimiter* is a single-character string."""
        if delimiter is not None and (
            not isinstance(delimiter, str) or len(delimiter) != 1
        ):
            raise ValueError(
                f"delimiter must be a single-character string. Got: {delimiter!r}",
            )

    def _validate_null_string(self, null_string: str | None) -> None:
        """Validate that *null_string* is a string."""
        if null_string is not None and not isinstance(null_string, str):
            raise ValueError(
                f"null_string must be a str. Got: {type(null_string).__name__}",
            )

    def _validate_quote_character(self, quote_character: str | None) -> None:
        """Validate that *quote_character* is a single-character string."""
        if quote_character is not None and (
            not isinstance(quote_character, str) or len(quote_character) != 1
        ):
            raise ValueError(
                f"quote_character must be a single-character string. "
                f"Got: {quote_character!r}",
            )

    def _validate_encoding(self, encoding: str | None) -> None:
        """Validate that *encoding* is a non-empty, whitespace-free string."""
        if encoding is not None and (
            not isinstance(encoding, str)
            or not encoding
            or any(c.isspace() for c in encoding)
        ):
            raise ValueError(
                f"encoding must be a non-empty string with no whitespace. "
                f"Got: {encoding!r}",
            )

    def _validate_column_list(
        self,
        columns: list[str] | None,
        param_name: str,
    ) -> None:
        """Validate that every element of *columns* is a model field name.

        Args:
            columns: List of column names to validate, or ``None``.
            param_name: Name of the parameter (for error messages).
        """
        if columns is not None:
            for col in columns:
                if col not in self._model_field_names:
                    raise ValueError(
                        f"{param_name} value '{col}' is not a field on "
                        f"{self.model.__name__}. Valid fields: "
                        f"{sorted(self._model_field_names)}",
                    )

    def _validate_temp_table_name(self, name: str) -> None:
        """Validate that *name* is a legal PostgreSQL identifier.

        Must match ``^[A-Za-z_][A-Za-z0-9_]{0,62}$``.
        """
        if not _TEMP_TABLE_NAME_RE.match(name):
            raise ValueError(
                "temp_table_name must match ^[A-Za-z_][A-Za-z0-9_]{0,62}$. "
                f"Got: {name!r}",
            )

    def _generate_temp_table_name(self) -> str:
        """Generate a random, valid temporary table name."""
        chars = string.ascii_letters + string.digits
        suffix = "".join(random.choices(chars, k=20))
        return f"tmp_{suffix}"

    # --------------------------------------------------------------------------
    # Pipeline steps
    # --------------------------------------------------------------------------

    def _build_field_definitions(self) -> list[tuple[str, str]]:
        """Return a list of (column_name, sql_type) pairs for the temp table."""
        definitions = []
        for col in self.data_columns:
            field = self.model._meta.get_field(col)
            db_type = field.db_type(connection)
            definitions.append((col, db_type.upper()))
        return definitions

    def _create_temp_table(self, cursor: CursorWrapper) -> None:
        """Step 1: Create a temporary table matching the CSV columns."""
        field_definitions = self._build_field_definitions()
        sql = render_template(
            "create.sql",
            temp_table_name=self.temp_table_name,
            field_definitions=field_definitions,
        )
        cursor.execute(sql)

    def _copy_data(self, cursor: CursorWrapper) -> None:
        """Step 2: Stream CSV data into the temp table via COPY FROM STDIN.

        Accesses the underlying psycopg cursor to perform the COPY operation.
        Uses duck typing to support both psycopg2 and psycopg3:
        - psycopg3 cursors expose a ``copy(sql)`` context-manager method.
        - psycopg2 cursors expose ``copy_expert(sql, file)``.
        """
        sql = render_template(
            "copy.sql",
            temp_table_name=self.temp_table_name,
            columns=self.data_columns,
            delimiter=self.delimiter,
            null_string=self.null_string,
            quote_character=self.quote_character,
            force_not_null=self.force_not_null,
            force_null=self.force_null,
            encoding=self.encoding,
        )
        self.data.seek(0)
        # Unwrap Django's CursorWrapper to access the psycopg-level cursor
        raw = cursor.cursor
        if hasattr(raw, "copy") and callable(raw.copy):
            # psycopg3 path: copy() is a context manager
            with raw.copy(sql) as copy:
                copy.write(self.data.read())
        else:
            # psycopg2 path: copy_expert streams from a file-like object
            raw.copy_expert(sql, self.data)

    def _merge_data(self, cursor: CursorWrapper) -> int:
        """Step 3: Move rows from the temp table into the target model table.

        Returns:
            Number of rows affected (inserted, updated, or deleted).
        """
        model_table = self.model._meta.db_table

        if self.method == "replace":
            # Delete all existing rows via the ORM — do NOT use raw TRUNCATE
            self.model.objects.all().delete()
            sql = render_template(
                "replace.sql",
                model_table_name=model_table,
                temp_table_name=self.temp_table_name,
                columns=self.data_columns,
            )
            cursor.execute(sql)
            return cursor.rowcount

        if self.method == "append":
            sql = render_template(
                "append.sql",
                model_table_name=model_table,
                temp_table_name=self.temp_table_name,
                columns=self.data_columns,
            )
            cursor.execute(sql)
            return cursor.rowcount

        # "update" and "upsert" both use PostgreSQL MERGE
        non_join_columns = [c for c in self.data_columns if c not in self.join_columns]

        if self.method == "update":
            sql = render_template(
                "update.sql",
                model_table_name=model_table,
                temp_table_name=self.temp_table_name,
                join_columns=self.join_columns,
                non_join_columns=non_join_columns,
            )
            cursor.execute(sql)
            return cursor.rowcount

        # method == "upsert"
        sql = render_template(
            "upsert.sql",
            model_table_name=model_table,
            temp_table_name=self.temp_table_name,
            join_columns=self.join_columns,
            non_join_columns=non_join_columns,
            all_columns=self.data_columns,
        )
        cursor.execute(sql)
        return cursor.rowcount

    def _drop_temp_table(self, cursor: CursorWrapper) -> None:
        """Step 4: Drop the temporary table."""
        sql = render_template("drop.sql", temp_table_name=self.temp_table_name)
        cursor.execute(sql)

    def _validate_pg_version(self) -> None:
        """Verify that the connected PostgreSQL server is version 15 or higher.

        The MERGE statement used by the 'update' and 'upsert' methods requires
        PostgreSQL 15+. We enforce this requirement unconditionally so that
        version mismatches are caught early, before any pipeline steps run.

        Raises:
            RuntimeError: If the server major version is less than 15.
        """
        # connection.pg_version is an integer like 150006 for PG 15.6
        pg_version = connection.pg_version
        major_version = pg_version // 10000
        if major_version < _MIN_PG_MAJOR_VERSION:
            raise RuntimeError(
                f"django-postgres-loader requires PostgreSQL "
                f"{_MIN_PG_MAJOR_VERSION} or higher. "
                f"Connected server reports version {major_version} "
                f"(pg_version={pg_version}).",
            )

    # --------------------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------------------

    def load(self) -> int:
        """Execute the full data load pipeline.

        The full pipeline runs inside ``transaction.atomic()``. If any step
        after CREATE raises an exception, the DROP step still executes
        (unless ``keep_temp_table=True``) before the exception propagates,
        leaving the database in the pre-load state.

        Returns:
            Number of rows affected by the merge step.
        """
        self._validate_pg_version()
        rows_affected = 0
        with transaction.atomic(), connection.cursor() as cursor:
            self._create_temp_table(cursor)
            try:
                self._copy_data(cursor)
                rows_affected = self._merge_data(cursor)
            finally:
                if not self.keep_temp_table:
                    self._drop_temp_table(cursor)
        return rows_affected
