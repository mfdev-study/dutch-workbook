from django.urls import path

from . import views

app_name = "dutch"

urlpatterns = [
    path("de-het/", views.quiz, name="quiz"),
    path("de-het/answer/", views.answer, name="answer"),
    path("de-het/result/", views.result, name="result"),
    path("de-het/reset/", views.reset, name="reset"),
]
