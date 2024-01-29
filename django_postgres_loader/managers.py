"""Managers for django-postgres-loader."""

# standard library imports
import io
from typing import Callable, Dict, List, Optional, Union

# third-party imports
from django.db import models

# local imports
from . import CopyLoader


class CopyLoadQuerySet(models.QuerySet):
    """Custom QuerySet supporting COPY-based load."""

    def load(
        self,
        data: Union[io.StringIO, str],
        operation: str = "append",
        truncate: Union[bool, models.QuerySet] = False,
        conflict_target: Optional[List[str]] = None,
        update_operation: Optional[
            Union[str, Callable, Dict[str, Optional[Union[str, Callable]]]]
        ] = None,
        field_mapping: Optional[Dict[str, str]] = None,
        delimiter: Optional[str] = None,
        null_string: Optional[str] = None,
        quote_character: Optional[str] = None,
        force_not_null: Optional[List[str]] = None,
        force_null: Optional[List[str]] = None,
        encoding: Optional[str] = None,
        temp_table_name: Optional[str] = None,
    ) -> int:
        """Load data into database via manager.

        Steps:
            1.  Validate value of [truncate] and, if truncation is desired, then
                perform the truncation.
            2.  Create a CopyLoader to perform the load.
            3.  Perform the load.
            4.  Return.

        Args:
            data (StringIO|str):
                The data to load. If a StringIO object, then must be
                CSV-formatted data. If a string, then must be a path to an
                existing CSV file.
            operation (str):
                The type of load to perform.
            truncate ([bool|QuerySet]):
                If provided as a boolean, then a flag indicating whether data
                should be deleted from the model before performing the load. If
                provided as a QuerySet, then all data in the QuerySet will be
                deleted. Note that QuerySet input should NOT include .delete().
            conflict_target ([list[str]]):
                The set of columns to use as the conflict target in the
                "ON CONFLICT" clause of the insert. Must be provided if
                [operation] is "safe_append", "update", or "upsert"; will not be
                used if [operation] is "append" or "replace". If provided, must
                be a subset of [model]'s columns.
            update_operation ([str|Callable|dict[str, [str|Callable]]:
                The operation to use when updating records. Must be provided if
                [operation] is "update" or "upsert"; will not be used if
                [operation] is "append", "safe_append", or "replace".

                May be provided as a string, function, or a dictionary whose
                keys are names of columns in [model] and whose values are
                operations. If a string is provided, the provided operation will
                be used to update all columns other than those specified in
                [conflict_target]. If a dictionary is provided, then its keys
                must be a subset of [model]'s columns (any excluded columns will
                not be updated) and its values must be valid update operations.
                If a function (Callable) is provided, then it must have two
                parameters: field_name, target_table_name; it must also return a
                string (this is NOT validated).
            field_mapping ([dict]):
                The mapping of columns in [data] (keys) to columns in [model]
                (values). If provided, keys must be subset of [data]'s columns
                and values must be columns in [model]. Keys and values must be
                unique. Any field in [data] that is not included as a key is
                assumed to map to the corresponding field of [model].
            delimiter ([str]):
                The character used to separate columns within each row of the
                file. If not provided, then the PostgreSQL default (",") will
                be used.
            null_string ([str]):
                The string that represents a null value. If not provided, then
                the PostgreSQL default ("") will be used.
            quote_character ([str]):
                The quoting character to be used when a data value is quoted.
                If not provided, then the PostgreSQL default ('"') will be used.
            force_not_null ([list[str]):
                The columns for which [null_string] is not to be cast to NULL.
            force_null ([list[str]]):
                The columns for which [null_string] should be cast to NULL, even
                if it has been quoted.
            encoding ([str]):
                The encoding method used in the file. If not provided, then the
                PostgreSQL default (client encoding) will be used.
            temp_table_name ([str]):
                The name to give the temporary table storing [data] before it
                is loaded into [model]'s database table. If not provided, then
                a name will be randomly generated.

        Returns (int):
            The number of rows affected by the load pipeline.
        """
        # Step 1
        if isinstance(truncate, bool):
            if truncate:
                self.model.objects.all().delete()
        elif isinstance(truncate, models.QuerySet):
            if truncate.model != self.model:
                raise ValueError(
                    f"QuerySet specifying data to truncate must come from {self.model.__name__}."
                )
            else:
                truncate.delete()

        # Step 2
        loader = CopyLoader(
            model=self.model,
            data=data,
            operation=operation,
            conflict_target=conflict_target,
            update_operation=update_operation,
            field_mapping=field_mapping,
            delimiter=delimiter,
            null_string=null_string,
            quote_character=quote_character,
            force_not_null=force_not_null,
            force_null=force_null,
            encoding=encoding,
            temp_table_name=temp_table_name,
        )

        # Step 3
        n_rows_affected = loader.load()

        # Step 4
        return n_rows_affected


CopyLoadManager = models.Manager.from_queryset(CopyLoadQuerySet)
