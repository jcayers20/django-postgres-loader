"""Handlers for loading data into the database."""

# standard library imports
import csv
import io
import logging
import sys
from typing import Any, Dict, List, Optional, Type, Union

# third-party imports
from django.db import models
from django.db import connections, NotSupportedError

# local imports
from django_postgres_loader import utils


class CopyLoader:
    """Load data from a CSV object into PostgreSQL database."""

    def __init__(
        self,
        model: Type[models.Model],
        data: Union[str, io.StringIO],
        operation: str,
        conflict_target: Optional[List[str]] = None,
        update_operation: Optional[Union[str, Dict[str, Optional[str]]]] = None,
        field_mapping: Optional[Dict[str, str]] = None,
        delimiter: Optional[str] = None,
        null_string: Optional[str] = None,
        quote_character: Optional[str] = None,
        force_not_null: Optional[List[str]] = None,
        force_null: Optional[List[str]] = None,
        encoding: Optional[str] = None,
        temp_table_name: Optional[str] = None,
    ):
        """Instantiate a CopyLoader instance.

        Create an object that can be used to load [data] into [model] using the
        specified [operation] and [update_operation] and using provided
        configuration details.

        Supported operations:
            "append":       Add [data] without performing any conflict check.
            "replace":      Remove all data from [model], then load [data].
            "safe_append":  Add [data], but do not add rows where
                            [conflict_target] matches that of an existing row.
            "update":       If [conflict_target] matches that of an existing
                            row, then update the row using [update_operation].
                            Otherwise, do nothing.
            "upsert":       If [conflict_target] matches that of an existing
                            row, then update the row using [update_operation].
                            Otherwise, insert a new row.

        Supported update operations ([old] = existing value; [new] = new value):
            "add":          [old] + [new]
            "subtract_new": [old] - [new]
            "subtract_old": [new] - [old]
            "multiply":     [old] * [new]
            "divide_new":   [old] / [new]
            "divide_old":   [new] / [old]
            "replace":      [new]
            "coalesce_new": COALESCE([new], [old])
            "coalesce_old": COALESCE([old], [new])
            "greatest":     GREATEST([old], [new])
            "least":        LEAST([old], [new])

        Args:
            model (models.Model):
                The model into which data will be loaded
            data (StringIO):
                The data to load into [model]. If a StringIO object, then must
                be CSV-formatted data. If a string, then must be a path to an
                existing CSV file.
            operation (str):
                The type of load to perform. See above for permissible values
                and descriptions.
            conflict_target ([list[str]]):
                The set of columns to use as the conflict target in the
                "ON CONFLICT" clause of the insert. Must be provided if
                [operation] is "safe_append", "update", or "upsert"; will not be
                used if [operation] is "append" or "replace". If provided, must
                be a subset of [data]'s columns.
            update_operation ([str|dict[str, [str]]:
                The operation to use when updating records. Must be provided if
                [operation] is "update" or "upsert"; will not be used if
                [operation] is "append", "safe_append", or "replace".

                May be provided as a string or a dictionary whose keys are names
                of columns in [data] and whose values are operations. If a
                string is provided, the provided operation will be used to
                update all columns other than those specified in
                [conflict_target]. If a dictionary is provided, then its keys
                must be a subset of [data]'s columns (any excluded columns will
                not be updated) and its values must be valid update operations.

                See above for permissible values and descriptions.
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
        """
        pass
