from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
]

urlpatterns += i18n_patterns(
    path("accounts/", include("accounts.urls")),
    path("words/", include("words.urls")),
    path("quiz/", include("quiz.urls")),
    path("progress/", include("progress.urls")),
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
)
