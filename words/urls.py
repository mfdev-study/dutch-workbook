from django.urls import path

from . import views

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
    path("graph/", views.word_graph, name="word_graph"),
    path("graph-data/", views.word_graph_json, name="word_graph_json"),
    path("learning-path/<int:word_id>/", views.learning_path, name="learning_path"),
    path("favorites/", views.favorites_list, name="favorites"),
    path("word/<int:word_id>/add-example/", views.add_example, name="add_example"),
    path("example/<int:example_id>/edit/", views.edit_example, name="edit_example"),
    path("example/<int:example_id>/delete/", views.delete_example, name="delete_example"),
    # AI Generation
    path("generate-words/", views.generate_words_view, name="generate_words"),
]
