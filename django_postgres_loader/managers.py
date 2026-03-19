"""Custom Django manager that exposes the CopyLoader pipeline."""

from typing import List, Optional

from django.db import models

from .load import CopyLoader


class CopyManager(models.Manager):
    """Django model manager for CSV loads into PostgreSQL."""

    def load(
        self,
        data,
        method: str,
        join_columns: Optional[List[str]] = None,
        delimiter: Optional[str] = None,
        null_string: Optional[str] = None,
        quote_character: Optional[str] = None,
        force_not_null: Optional[List[str]] = None,
        force_null: Optional[List[str]] = None,
        encoding: Optional[str] = None,
        temp_table_name: Optional[str] = None,
        keep_temp_table: bool = False,
    ) -> int:
        """Load CSV data into the model table using a temporary-table pipeline.

        Args:
            data: Input data as ``io.StringIO``, ``pathlib.Path``, or a
                ``pandas.DataFrame``.
            method: One of ``replace``, ``append``, ``update``, or ``upsert``.
            join_columns: Columns used to join target and staging rows for
                ``update`` and ``upsert`` methods.
            delimiter: Optional single-character CSV delimiter.
            null_string: Optional NULL sentinel for PostgreSQL COPY.
            quote_character: Optional single-character CSV quote character.
            force_not_null: Optional list of columns for ``FORCE_NOT_NULL``.
            force_null: Optional list of columns for ``FORCE_NULL``.
            encoding: Optional COPY encoding value.
            temp_table_name: Optional explicit temporary table name.
            keep_temp_table: If ``True``, skips temp-table drop in ``load()``.

        Returns:
            Number of rows affected by the merge step.
        """
        loader = CopyLoader(
            model=self.model,
            data=data,
            method=method,
            join_columns=join_columns,
            delimiter=delimiter,
            null_string=null_string,
            quote_character=quote_character,
            force_not_null=force_not_null,
            force_null=force_null,
            encoding=encoding,
            temp_table_name=temp_table_name,
            keep_temp_table=keep_temp_table,
        )
        return loader.load()
