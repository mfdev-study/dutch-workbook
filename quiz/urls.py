from django.urls import path

from . import views

urlpatterns = [
    path("", views.quiz_home, name="quiz_home"),
    path("start/<str:quiz_type>/", views.start_quiz, name="start_quiz"),
    path("question/", views.quiz_question, name="quiz_question"),
    path("submit/", views.submit_answer, name="submit_answer"),
    path("results/", views.quiz_results, name="quiz_results"),
    path("history/", views.quiz_history, name="quiz_history"),
]
