"""Module-level constants and shared Jinja2 environment for SQL templates."""

from pathlib import Path

import jinja2

# Valid insertion methods supported by CopyManager.load()
VALID_METHODS = ("replace", "append", "update", "upsert")

# Path to the SQL template directory
_TEMPLATE_DIR = Path(__file__).parent / "templates" / "sql"

# Jinja2 environment — autoescape=False is REQUIRED so SQL is not HTML-escaped
_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,
)


def render_template(template_name: str, **context: object) -> str:
    """Render a SQL template with the given context variables.

    Args:
        template_name: Filename of the template (e.g. "create.sql").
        **context: Variables made available inside the template.

    Returns:
        The rendered SQL string.
    """
    template = _env.get_template(template_name)
    return template.render(**context)
