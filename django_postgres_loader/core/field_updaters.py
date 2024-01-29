"""Functions to generate SQL for various field updates."""


def replace(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet to replace value of field in target table.

    Note that [target_table_name] is not used; it is only present as this is
    a requirement of the update structure.

    Steps:
        1.  Enclose [field_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet to replace [target_table_name].[field_name] with the value
        found in the new table.
    """
    # Step 1
    field = f'"{field_name}"'

    # Step 2
    snippet = f"""{field} = EXCLUDED.{field}"""

    # Step 3
    return snippet


def add(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet to add new value to existing value of field.

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet to add new value to existing value of field.
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = f"""{field} = {target_table}.{field} + EXCLUDED.{field}"""

    # Step 3
    return snippet


def subtract_new(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet to subtract new value from existing value of field.

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet to subtract new value from existing value of field.
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = f"""{field} = {target_table}.{field} - EXCLUDED.{field}"""

    # Step 3
    return snippet


def subtract_old(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet to subtract existing value from new value of field.

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet to subtract new value from existing value of field.
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = f"""{field} = EXCLUDED.{field} - {target_table}.{field}"""

    # Step 3
    return snippet


def multiply(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet to multiply existing value of field by new value.

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet to multiply existing value of field by new value.
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = f"""{field} = EXCLUDED.{field} * {target_table}.{field}"""

    # Step 3
    return snippet


def divide_new(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet to divide existing value of field by new value.

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet to divide existing value of field by new value.
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = f"""{field} = {target_table}.{field} / EXCLUDED.{field}"""

    # Step 3
    return snippet


def divide_old(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet to divide new value by existing value of field.

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet to divide new value by existing value of field.
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = f"""{field} = EXCLUDED.{field} / {target_table}.{field}"""

    # Step 3
    return snippet


def coalesce_new(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet for a COALESCE update, preferring new value of field.

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet for a COALESCE update, preferring new value of field.
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = (
        f"""{field} = COALESCE(EXCLUDED.{field}, {target_table}.{field})"""
    )

    # Step 3
    return snippet


def coalesce_old(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet for a COALESCE update, preferring old value of field.

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet for a COALESCE update, preferring old value of field.
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = (
        f"""{field} = COALESCE({target_table}.{field}, EXCLUDED.{field})"""
    )

    # Step 3
    return snippet


def greatest(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet for an update using GREATEST().

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet for an update using GREATEST().
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = (
        f"""{field} = GREATEST({target_table}.{field}, EXCLUDED.{field})"""
    )

    # Step 3
    return snippet


def least(
    field_name: str,
    target_table_name: str,
) -> str:
    """Write SQL snippet for an update using LEAST().

    Steps:
        1.  Enclose [field_name] and [target_table_name] in double-quotes.
        2.  Build snippet.
        3.  Return.

    Args:
        field_name (str):
            The name of the field being updated.
        target_table_name (str):
            The name of the table being updated.

    Returns (str):
        SQL snippet for an update using LEAST().
    """
    # Step 1
    field = f'"{field_name}"'
    target_table = f'"{target_table_name}"'

    # Step 2
    snippet = f"""{field} = LEAST({target_table}.{field}, EXCLUDED.{field})"""

    # Step 3
    return snippet
