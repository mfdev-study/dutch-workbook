from django import template

from words.models import CategorizedWord

register = template.Library()


@register.simple_tag
def get_word_categories(word):
    """Get all categories for a given word"""
    categorized_words = CategorizedWord.objects.filter(word=word).select_related("category")
    return [cw.category for cw in categorized_words]
