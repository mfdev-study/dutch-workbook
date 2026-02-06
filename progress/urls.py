from django.urls import path
from . import views

urlpatterns = [
    path("", views.progress_dashboard, name="progress"),
    path("streak/", views.streak_view, name="streak"),
]
