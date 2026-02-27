from django.db import DatabaseError
from django.db.utils import OperationalError, ProgrammingError

from .models import Category


def menu_categories(request):
    """Return published categories for the top navigation menu."""
    try:
        categories = list(
            Category.objects.filter(
                is_published=True
            ).order_by('title')
        )
    except (DatabaseError, OperationalError, ProgrammingError, RuntimeError):
        categories = []
    return {'menu_categories': categories}
