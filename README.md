# coldfront-allocation-blueprint

A [ColdFront](https://coldfront.readthedocs.io/) plugin that gives new allocations a resource's
standard attributes. You define a blueprint for a resource: the allocation attributes every
allocation of it should have, each with an initial value. When someone requests an allocation of
that resource, the plugin adds those attributes to it.

An initial value can be fixed text, or can take values from the allocation's project or
resource: `/cluster/tufts/{project.Group}` becomes `/cluster/tufts/smithlab` for a project whose
`Group` attribute is `smithlab`.

## How it works

1. ColdFront sends its `allocation_new` signal when an allocation is created.
2. The plugin queues a django-q task, `allocation_blueprint.tasks.apply_blueprint`, for the new
   allocation.
3. The task finds the blueprint for the allocation's resource and, for each attribute in it,
   creates that allocation attribute with the blueprint's value. An attribute the allocation
   already has is left as it is, so the task never overwrites a value someone set.

The attributes are added by a background task, so they appear shortly after the allocation is
created, and only while the django-q cluster (`coldfront qcluster`) is running.

## Requirements

- ColdFront 1.1.7 or later (but not 2.x)
- Python 3.10 or later
- A running django-q cluster

## Installation

1. Install the plugin into ColdFront's environment:

   ```bash
   uv add "coldfront-allocation-blueprint @ git+https://github.com/Tufts-Technology-Services/coldfront-allocation-blueprint.git"
   ```

2. Add the app to `INSTALLED_APPS` in `local_settings.py`:

   ```python
   from coldfront.config.base import INSTALLED_APPS

   INSTALLED_APPS += ["allocation_blueprint"]
   ```

3. Turn the plugin on in ColdFront's environment (e.g. `/etc/coldfront/coldfront.env`):

   ```
   BLUEPRINT_ENABLE_SIGNALS=True
   ```

   It's off by default: with it off, the plugin is installed, and blueprints can be edited, but
   new allocations don't get their attributes.

4. Restart ColdFront and the django-q cluster.

The plugin's two models are new database tables. It doesn't ship migrations yet, so create its
tables before using it.

## Configuration

| Setting | Default | Meaning |
| --- | --- | --- |
| `BLUEPRINT_ENABLE_SIGNALS` | `False` | Add a blueprint's attributes to each new allocation of its resource |

## Defining blueprints

Blueprints are managed in the Django admin, under **Allocation Blueprints › Allocation blueprints**.
There's one blueprint per resource, and the list shows each with its attributes.

A blueprint's page has its resource and, below it, a table of its attributes: each row is an
allocation attribute type and its initial value. Add a row for each attribute new allocations
should get, and tick **Delete?** on a row to remove it.

The allocation attribute types themselves are ColdFront's, set up as usual.

### Initial values

An initial value is used as it is, unless it contains placeholders in braces:

| Placeholder | Replaced with |
| --- | --- |
| `{project.<name>}` | The value of the allocation's project's attribute `<name>` |
| `{resource.<name>}` | The value of the allocation's resource's attribute `<name>` |

- Attribute names are matched ignoring case, and may be quoted: `{project."Project Key"}`.
- A value can mix text and several placeholders: `{resource.Root}/{project.Group}`.
- If the project or resource has no attribute of that name, that attribute isn't created, but
  the others still are. Then the task fails, naming each attribute it couldn't fill in and why,
  so it shows among the django-q failed tasks: create those attributes by hand.
- An empty initial value creates the attribute with an empty value, for someone to fill in later.

## Development

```bash
uv sync
uv run pytest
uv run ruff check
uv run ruff format --check
uv run pre-commit install
```

The tests run against ColdFront's own settings with an in-memory SQLite database
(`allocation_blueprint/tests/settings.py`).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
