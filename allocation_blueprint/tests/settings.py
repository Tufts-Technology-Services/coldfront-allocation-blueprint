"""Django settings for the plugin's test suite.

Builds on ColdFront's own settings so the core apps and models match a real deployment, then
swaps in an in-memory database so the tests need no services.
"""

from coldfront.config.settings import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, "allocation_blueprint"]  # noqa: F405

# allocation_blueprint/urls.py is mounted by the deployment's local_urls.py, so the tests mount it too
ROOT_URLCONF = "allocation_blueprint.tests.urls"

# In memory, whatever DB_URL says: ColdFront's settings take the database from it, and in a shell
# where it names a real server, the tests would create their database there.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# a deliberately weak hasher: creating users is much faster, and nothing here checks its strength
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
