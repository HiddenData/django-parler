from django.conf import settings
from django.utils.translation import get_language
from django.views.generic import ListView, DetailView
from .models import Article
from parler.views import TranslatableSlugMixin


JSON_BACKEND = settings.PARLER_BACKEND == 'json'


class BaseArticleMixin(object):
    # Only show published articles.
    def get_queryset(self):
        return super(BaseArticleMixin, self).get_queryset().filter(published=True)


class ArticleListView(BaseArticleMixin, ListView):
    model = Article
    template_name = 'article/list.html'

    def get_queryset(self):
        # Only show objects translated in the current language.
        language = get_language()
        if JSON_BACKEND:
            return super(ArticleListView, self).get_queryset().filter(translations_data__has=language)
        else:
            return super(ArticleListView, self).get_queryset().filter(translations__language_code=language)


class ArticleDetailView(BaseArticleMixin, TranslatableSlugMixin, DetailView):
    model = Article
    template_name = 'article/details.html'  # This works as expected
