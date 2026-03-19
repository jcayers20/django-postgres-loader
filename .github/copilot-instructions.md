# Copilot Instructions — django-postgres-loader

This file contains everything a developer or AI agent needs to understand and work within this codebase.

---

## Project Purpose and Architecture Overview

`django-postgres-loader` is a Django library that exposes a custom model manager (`CopyManager`) for bulk-loading CSV data into a PostgreSQL table. It uses a **four-step pipeline** that leverages PostgreSQL's `COPY` command for high-throughput data ingestion:

1. **Create temp table** — a `CREATE TEMPORARY TABLE` with the same column definitions as the target model's database table.
2. **COPY into temp table** — stream CSV data into the temp table using `COPY ... FROM STDIN WITH CSV HEADER`.
3. **Merge into target table** — move data from the temp table into the target model table using the correct SQL strategy for the chosen `method`.
4. **Drop temp table** — unconditionally drop the temp table (unless `keep_temp_table=True`).

The entire pipeline is wrapped in `django.db.transaction.atomic()`. The DROP step is in a `try/finally` block to ensure it runs even if an earlier step raises an exception.

### Package Layout

```
django_postgres_loader/
  __init__.py            # exports CopyManager
  managers.py            # defines CopyManager (models.Manager subclass)
  load.py                # defines CopyLoader (the pipeline implementation)
  core/
    __init__.py
    definitions.py       # VALID_METHODS, Jinja2 environment, render_template()
    field_updaters.py    # intentionally empty (v0.2.0)
    templates/sql/       # Jinja2 SQL templates
      create.sql
      copy.sql
      replace.sql
      append.sql
      update.sql
      upsert.sql
      drop.sql
  utils/
    __init__.py

tests/
  settings.py            # Django settings for the test suite
  models.py              # test Django models
  conftest.py            # pytest fixtures
  test_load.py           # test suite
```

---

## Insertion Methods

### `"replace"`
Deletes all existing rows using `model.objects.all().delete()` (NOT raw `TRUNCATE`), then inserts all rows from the temp table using a plain `INSERT INTO ... SELECT ... FROM temp_table`. Does NOT use `MERGE`.

### `"append"`
Inserts all rows from the temp table unconditionally using `INSERT INTO ... SELECT ... FROM temp_table`. No conflict handling. Does NOT use `MERGE`.

### `"update"`
Uses PostgreSQL `MERGE` with **only** `WHEN MATCHED THEN UPDATE SET`. Rows in the temp table that have no match in the target are silently ignored — there is NO `WHEN NOT MATCHED` clause. All non-join columns are overwritten with the source values (simple replacement, no per-column arithmetic).

### `"upsert"`
Uses PostgreSQL `MERGE` with both `WHEN MATCHED THEN UPDATE SET` and `WHEN NOT MATCHED THEN INSERT`. Matched rows are updated; unmatched rows are inserted. All non-join columns are simple-replaced on update.

### Summary

| Method    | Uses MERGE? | WHEN MATCHED? | WHEN NOT MATCHED? |
|-----------|-------------|---------------|-------------------|
| replace   | No          | —             | —                 |
| append    | No          | —             | —                 |
| update    | Yes         | UPDATE SET    | (omitted)         |
| upsert    | Yes         | UPDATE SET    | INSERT            |

---

## SQL Template System

All SQL is written as Jinja2 templates in `django_postgres_loader/core/templates/sql/`.

### Loading Templates

Templates are loaded via a **module-level `jinja2.Environment`** in `django_postgres_loader/core/definitions.py`:

```python
from pathlib import Path
import jinja2

_TEMPLATE_DIR = Path(__file__).parent / "templates" / "sql"

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,  # REQUIRED — autoescape corrupts SQL
)
```

**`autoescape=False` is required.** The Django Jinja2 backend auto-escapes output (converting `"` to `&quot;` etc.) which would corrupt SQL. Do NOT use the Django Jinja2 backend here.

### Rendering Templates

Use the `render_template()` helper:

```python
from django_postgres_loader.core.definitions import render_template

sql = render_template("append.sql", model_table_name="my_table", ...)
```

### Template Variables

| Template               | Key Variables                                                  |
|------------------------|---------------------------------------------------------------|
| `create.sql`           | `temp_table_name`, `field_definitions` (list of `(col, type)` tuples) |
| `copy.sql`             | `temp_table_name`, `columns`, `delimiter`, `null_string`, `quote_character`, `force_not_null`, `force_null`, `encoding` |
| `replace.sql`          | `model_table_name`, `temp_table_name`, `columns`              |
| `append.sql`           | `model_table_name`, `temp_table_name`, `columns`              |
| `update.sql`           | `model_table_name`, `temp_table_name`, `join_columns`, `non_join_columns` |
| `upsert.sql`           | `model_table_name`, `temp_table_name`, `join_columns`, `non_join_columns`, `all_columns` |
| `drop.sql`             | `temp_table_name`                                             |

### Column Name Quoting

All column names in SQL templates are double-quoted (`"column_name"`) to prevent SQL injection and reserved-word conflicts.

---

## Manager Registration

Register `CopyManager` on any Django model:

```python
from django.db import models
from django_postgres_loader import CopyManager

class MyModel(models.Model):
    name = models.CharField(max_length=100)

    objects = CopyManager()
```

Then call:

```pythonff
import io

MyModel.objects.load(
    data=io.StringIO("name\nAlice\nBob\n"),
    method="append",
)
```

---

## Accepted Data Source Types

The `data` parameter of `CopyManager.load()` accepts exactly three types:

| Type | Behaviour |
|------|-----------|
| `io.StringIO` | Rewound to position 0, used as-is. |
| `pathlib.Path` | File is validated (exists, readable, parseable as CSV), then read into `StringIO`. |
| `pandas.DataFrame` | Converted via `data.to_csv(index=False)` and wrapped in `StringIO`. |

**Bare `str` paths are NOT accepted.** Passing a `str` raises `TypeError`. Always use `pathlib.Path` for file references.

Pandas is NOT a required dependency. The code detects it at runtime with `try: import pandas as pd`.

---

## Security Approach

### Column Name Validation (Allow-List)

All column names from user input — including `join_columns`, `force_not_null`, `force_null`, and the CSV header row — are validated against the model's actual field list before being used in SQL. Any unrecognized column name raises `ValueError`.

### COPY Parameter Validation

| Parameter       | Rule                                                              |
|-----------------|------------------------------------------------------------------|
| `delimiter`     | Single-character `str`                                           |
| `quote_character` | Single-character `str`                                         |
| `encoding`      | Non-empty `str` with no whitespace                               |
| `null_string`   | Any `str` (including empty string)                               |
| `force_not_null` | Each element in model's field allow-list                        |
| `force_null`    | Each element in model's field allow-list                         |
| `temp_table_name` | Must match `^[A-Za-z_][A-Za-z0-9_]{0,62}$`                    |

### No Raw SQL Injection

Column names are never directly interpolated into SQL strings. They are always passed through the Jinja2 template context (which generates double-quoted identifiers) after being allow-list validated.

---

## Transaction and Error Handling

The `load()` method:

```python
with transaction.atomic():
    with connection.cursor() as cursor:
        self._create_temp_table(cursor)
        try:
            self._copy_data(cursor)
            rows_affected = self._merge_data(cursor)
        finally:
            if not self.keep_temp_table:
                self._drop_temp_table(cursor)
```

- **`transaction.atomic()`** — any failure rolls back all changes to the target table.
- **`try/finally`** — the DROP step runs even if COPY or merge raises an exception, preventing temp table accumulation.
- **`keep_temp_table=True`** — skips the DROP entirely so the temp table can be inspected after a failure.

---

## Test Infrastructure

### Running Tests

```bash
# From the project root, with the virtualenv active:
pytest
```

Database credentials are read from libpq environment variables:

```bash
export PGDATABASE=mydb
export PGUSER=myuser
export PGPASSWORD=mypassword
export PGHOST=localhost
export PGPORT=5432
pytest
```

### Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "tests.settings"
addopts = "--nomigrations --reuse-db"
```

`--nomigrations` uses `CREATE TABLE` directly instead of running migrations.
`--reuse-db` reuses the test database between runs for faster iteration.

### Test Models (`tests/models.py`)

| Model               | Purpose                                                          |
|---------------------|------------------------------------------------------------------|
| `SimpleModel`       | All non-nullable fields, BigAutoField PK — tests auto-field exemption |
| `NullableFieldModel` | Mix of nullable and non-nullable fields                         |
| `NaturalKeyModel`   | Non-auto primary key — PK must appear in CSV                    |
| `UpsertModel`       | Has a natural join key (`identifier`) for update/upsert tests   |

All models have `app_label = "tests"` and use `CopyManager`.

### Test Fixtures (`tests/conftest.py`)

Key fixtures:
- `simple_csv_stringio` — `StringIO` for `SimpleModel`
- `simple_csv_path` — `pathlib.Path` to a temp CSV file
- `simple_csv_dataframe` — `pandas.DataFrame` (test skipped if pandas absent)
- `upsert_csv_stringio` / `upsert_csv_updated_stringio` — initial and updated data for upsert tests
- `natural_key_csv_stringio` — data for `NaturalKeyModel`
- `nullable_csv_stringio` — minimal CSV (required fields only) for `NullableFieldModel`

---

## Features Intentionally Omitted (Deferred to Future Release)

### `safe_append` Operation
Inserts rows that have no existing match (skip duplicates). Was previously implemented with `ON CONFLICT DO NOTHING`. May be revisited using PostgreSQL `MERGE ... WHEN NOT MATCHED THEN INSERT` with a suitable join predicate.

### Configurable Per-Column Update Operations
The previous implementation allowed per-column update formulas (add, multiply, coalesce). The new design performs simple value replacement for all updates. May be revisited in a future release.

### Field Mapping
The previous implementation allowed mapping CSV column names to model field names. The new design requires CSV column names to exactly match model field names. May be revisited in a future release.

---

## Version Requirements

| Requirement | Minimum Version |
|-------------|-----------------|
| Python      | 3.10            |
| Django      | 4.2             |
| PostgreSQL  | 15              |
| Jinja2      | 3.1             |

---

## Code Style Expectations

- **Docstrings** — required on all classes, methods, and functions.
- **Path operations** — use `pathlib.Path` exclusively. Never use `os.path`.
- **No bare `str` file paths** — always use `pathlib.Path` for file references.
- **No required pandas dependency** — detect `pandas` at runtime with `try: import pandas`.
- **No Django Jinja2 backend** — use `jinja2.Environment` directly with `autoescape=False`.
- **All column names double-quoted in SQL** — prevents injection and reserved-word conflicts.
