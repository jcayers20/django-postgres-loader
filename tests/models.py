"""Django models used by the test suite."""

from django.db import models

from django_postgres_loader import CopyManager


class SimpleModel(models.Model):
    """Model with all non-nullable fields and a BigAutoField PK."""

    name = models.CharField(max_length=100)
    value = models.IntegerField()

    objects = CopyManager()

    class Meta:
        """Attach model to the tests app."""

        app_label = "tests"


class NullableFieldModel(models.Model):
    """Model with a mix of nullable and non-nullable fields."""

    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    objects = CopyManager()

    class Meta:
        """Attach model to the tests app."""

        app_label = "tests"


class NaturalKeyModel(models.Model):
    """Model with a non-auto primary key."""

    code = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200)

    objects = CopyManager()

    class Meta:
        """Attach model to the tests app."""

        app_label = "tests"


class UpsertModel(models.Model):
    """Model with a natural join key for update/upsert tests."""

    identifier = models.CharField(max_length=100, unique=True)
    payload = models.TextField()

    objects = CopyManager()

    class Meta:
        """Attach model to the tests app."""

        app_label = "tests"


class RelatedModel(models.Model):
    """Model with a ForeignKey to SimpleModel to exercise relation field skips."""

    simple = models.ForeignKey(SimpleModel, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)

    objects = CopyManager()

    class Meta:
        """Attach model to the tests app."""

        app_label = "tests"
