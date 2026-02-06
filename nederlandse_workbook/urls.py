from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("words/", include("words.urls")),
    path("quiz/", include("quiz.urls")),
    path("progress/", include("progress.urls")),
    path("", RedirectView.as_view(url="words/", permanent=False)),
]
