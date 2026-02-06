from django.urls import path

from . import category_views, views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("browse/", views.browse_words, name="browse"),
    path("add/", views.add_word, name="add_word"),
    path("word/<int:word_id>/", views.word_detail, name="word_detail"),
    path("word/<int:word_id>/add-flashcard/", views.add_flashcard, name="add_flashcard"),
    path(
        "word/<int:word_id>/remove-flashcard/",
        views.remove_flashcard,
        name="remove_flashcard",
    ),
    path(
        "word/<int:word_id>/toggle-favorite/",
        views.toggle_favorite,
        name="toggle_favorite",
    ),
    path("flashcards/", views.flashcards_review, name="flashcards"),
    path("flashcards/rate/<int:card_id>/<str:rating>/", views.rate_card, name="rate_card"),
    path("favorites/", views.favorites_list, name="favorites"),
    path("word/<int:word_id>/add-example/", views.add_example, name="add_example"),
    path("example/<int:example_id>/edit/", views.edit_example, name="edit_example"),
    path("example/<int:example_id>/delete/", views.delete_example, name="delete_example"),
    # Category URLs
    path("categories/", category_views.categories_list, name="categories_list"),
    path("categories/create/", category_views.create_category, name="create_category"),
    path(
        "categories/<int:category_id>/",
        category_views.category_detail,
        name="category_detail",
    ),
    path(
        "categories/<int:category_id>/edit/",
        category_views.edit_category,
        name="edit_category",
    ),
    path(
        "categories/<int:category_id>/delete/",
        category_views.delete_category,
        name="delete_category",
    ),
    path(
        "word/<int:word_id>/add-to-category/",
        category_views.add_to_category,
        name="add_to_category",
    ),
    path(
        "word/<int:word_id>/remove-from-category/<int:category_id>/",
        category_views.remove_from_category,
        name="remove_from_category",
    ),
    # AI Generation
    path("generate-words/", views.generate_words_view, name="generate_words"),
]
