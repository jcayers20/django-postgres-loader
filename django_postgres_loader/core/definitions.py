"""Variable definitions for use throughout package."""

# standard library imports
import os

SQL_TEMPLATE_DIR = os.path.join(
    os.path.dirname(__file__),
    "templates",
    "sql",
)

PERMITTED_OPERATIONS = [
    "append",
    "safe_append",
    "update",
    "upsert",
]

PERMITTED_UPDATE_OPERATIONS = [
    "add",
    "subtract_new",
    "subtract_old",
    "multiply",
    "divide_new",
    "divide_old",
    "replace",
    "coalesce_new",
    "coalesce_old",
    "greatest",
    "least",
    None,
]
