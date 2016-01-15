#!/usr/bin/env python
import sys
import django
from django.conf import settings, global_settings as default_settings
from django.core.management import execute_from_command_line
from os import path

if not settings.configured:
    module_root = path.dirname(path.realpath(__file__))

    sys.path.insert(0, path.join(module_root, 'example'))

    settings.configure(
        DEBUG = False,  # will be False anyway by DjangoTestRunner.
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
                'NAME': 'parler_example',
                'TEST_NAME': 'parler_example_test',
                'USER': 'printbox',
                'PASSWORD': 'printbox',
                'HOST': 'localhost',
                'PORT': '',
                'ATOMIC_REQUESTS': True,
            }
        },
        TEMPLATE_DEBUG = True,
        TEMPLATE_LOADERS = (
            'django.template.loaders.app_directories.Loader',
            'django.template.loaders.filesystem.Loader',
        ),
        TEMPLATE_CONTEXT_PROCESSORS = default_settings.TEMPLATE_CONTEXT_PROCESSORS + (
            'django.core.context_processors.request',
        ),
        INSTALLED_APPS = (
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sites',
            'django.contrib.admin',
            'django.contrib.sessions',
            'parler',
            'parler.tests.testapp',
            'article',
            'theme1',
        ),
        # we define MIDDLEWARE_CLASSES explicitly, the default were changed in django 1.7
        MIDDLEWARE_CLASSES=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.locale.LocaleMiddleware',  # / will be redirected to /<locale>/
        ),
        ROOT_URLCONF = 'example.urls',
        TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner' if django.VERSION < (1,6) else 'django.test.runner.DiscoverRunner',

        SITE_ID = 4,
        LANGUAGE_CODE = 'en',
        PARLER_LANGUAGES = {
            4: (
                {'code': 'nl'},
                {'code': 'de'},
                {'code': 'en'},
            ),
            'default': {
                'fallbacks': ['en'],
            },
        },
        PARLER_BACKEND = 'json',
    )


def runtests():
    argv = sys.argv[:1] + ['test', 'parler', 'article'] + sys.argv[1:]
    #argv = sys.argv[:1] + ['test', 'parler.tests.test_query_count.QueryCountTests.test_model_cache_queries'] + sys.argv[1:]
    #argv = sys.argv[:1] + ['test', 'parler.tests.test_xxx.XxxTests.test_xxx'] + sys.argv[1:]
    execute_from_command_line(argv)

if __name__ == '__main__':
    runtests()