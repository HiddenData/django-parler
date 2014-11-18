# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.forms.models import modelform_factory

from parler import appsettings
from parler.forms import _get_model_form_field, _get_mro_attribute, \
    TranslatedField
from parler.models import TranslationDoesNotExist
from parler.utils import compat

from django.conf import settings
from django.contrib.admin.options import ModelAdmin
from django.forms import ModelForm
from django.forms.models import ModelFormMetaclass
from django.utils.translation import get_language


def _replace_field(fields, name, replacement):
    new_fields = []
    new_fields.extend(fields[:fields.index(name)])
    new_fields.extend(replacement)
    new_fields.extend(fields[fields.index(name) + 1:])
    return tuple(new_fields)


def _get_available_language_codes():
    codes = []
    site_id = getattr(settings, 'SITE_ID', None)
    for lang_dict in appsettings.PARLER_LANGUAGES.get(site_id, ()):
        codes.append(lang_dict['code'])

    return codes


def _get_translated_fields_names(name):
    return [
        (code, '{}_{}'.format(name, code))
        for code in _get_available_language_codes()
    ]


def _get_default_language():
    return appsettings.PARLER_DEFAULT_LANGUAGE_CODE


def _handle_translation_model(bases, attrs, translations_model, form_new_meta,
                              form_meta, form_base_fields, translated_fields):
    """
    Add translation fields for each language to form
    """

    fields = getattr(form_new_meta, 'fields', form_meta.fields)
    exclude = \
        getattr(form_new_meta, 'exclude', form_meta.exclude) or ()
    widgets = \
        getattr(form_new_meta, 'widgets', form_meta.widgets) or ()
    formfield_callback = attrs.get('formfield_callback', None)

    if fields == '__all__':
        fields = None

    for f_name in translations_model.get_translated_fields():
        # Add translated field if not already added, and respect
        # exclude options.
        if f_name in translated_fields:
            attrs[f_name] = _get_model_form_field(
                translations_model, f_name,
                formfield_callback=formfield_callback,
                **translated_fields[f_name].kwargs)

        # The next code holds the same logic as fields_for_model()
        # The f.editable check happens in _get_model_form_field()
        elif f_name not in form_base_fields \
                and (fields is None or f_name in fields) \
                and f_name not in exclude \
                and not f_name in attrs:

            # Get declared widget kwargs
            if f_name in widgets:
                # Not combined with declared fields (e.g. the
                # TranslatedField placeholder)
                kwargs = {'widget': widgets[f_name]}
            else:
                kwargs = {}

            # See if this formfield was previously defined using a
            # TranslatedField placeholder.
            placeholder = _get_mro_attribute(bases, f_name)
            if placeholder and isinstance(placeholder,
                                          TranslatedField):
                kwargs.update(placeholder.kwargs)

            if not translations_model._meta.get_field(f_name).editable:
                continue

            translated_fields_names = _get_translated_fields_names(f_name)
            # replace original field name with translated fields names
            if fields is not None:
                replacement = zip(*translated_fields_names)[1]
                form_new_meta.fields = _replace_field(
                    fields or [f_name], f_name, replacement)

            # store translated fields in form
            for code, t_name in translated_fields_names:
                formfield = _get_model_form_field(
                    translations_model, f_name,
                    formfield_callback=formfield_callback, **kwargs)
                formfield.required = code == _get_default_language()
                formfield.label += ' ({})'.format(code)
                formfield.language_code = code
                attrs[t_name] = formfield


class TranslatableModelFormMetaclass(ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):
        create_cls = lambda: \
            super(TranslatableModelFormMetaclass, mcs).__new__(
                mcs, name, bases, attrs)

        # Before constructing class, fetch attributes from bases list.
        form_meta = _get_mro_attribute(bases, '_meta')

        # set by previous class level.
        form_base_fields = _get_mro_attribute(bases, 'base_fields', {})

        if not form_meta:
            return create_cls()

        # Not declaring the base class itself, this is a subclass.

        # Read the model from the 'Meta' attribute. This even works in the admin,
        # as `modelform_factory()` includes a 'Meta' attribute.
        # The other options can be read from the base classes.
        form_new_meta = attrs.get('Meta', form_meta)
        form_model = form_new_meta.model if form_new_meta else form_meta.model

        # Detect all placeholders at this class level.
        translated_fields = [
            f_name for f_name, attr_value in attrs.items()
            if isinstance(attr_value, TranslatedField)
        ]

        if not form_model:
            return create_cls()

        for translations_model in form_model._parler_meta.get_all_models():
            _handle_translation_model(
                bases, attrs, translations_model, form_new_meta, form_meta,
                form_base_fields, translated_fields)

        # Call the super class with updated `attrs` dict.
        return create_cls()


class TranslatableModelFormMixin(ModelForm):
    """
    Handles multipile translations for fields in single form
    """

    def __init__(self, *args, **kwargs):
        super(TranslatableModelFormMixin, self).__init__(*args, **kwargs)

        # Load the initial values for the translated fields
        instance = kwargs.get('instance', None)
        if not instance:
            return

        # for each translation meta
        for meta in instance._parler_meta:
            # for each translated field
            for field in meta.get_translated_fields():
                # for each language for that field
                for code, code_field in _get_translated_fields_names(field):
                    try:
                        translation = instance._get_translated_model(
                            meta=meta, language_code=code)
                    except TranslationDoesNotExist:
                        continue

                    self.initial.setdefault(
                        code_field, getattr(translation, field))

    def _post_clean(self):
        self.save_translated_fields()

        # Perform the regular clean checks, this also updates self.instance
        super(TranslatableModelFormMixin, self)._post_clean()

    def _get_all_translated_fields_names(self):
        for meta in self.instance._parler_meta:
            for field in meta.get_translated_fields():
                yield field

    def save_translated_fields(self):
        for code in _get_available_language_codes():
            self.instance.set_current_language(code)
            for field in self._get_all_translated_fields_names():
                code_field = dict(_get_translated_fields_names(field))[code]
                try:
                    value = self.cleaned_data[code_field]
                except KeyError:
                    continue

                setattr(self.instance, field, value)

        # Switch instance back to original language
        self.instance.set_current_language(get_language())


class TranslatableModelForm(
        compat.with_metaclass(TranslatableModelFormMetaclass,
                              TranslatableModelFormMixin,
                              ModelForm)):
    """
    The model form to use for translated models.
    """
    pass


class TranslatableAdmin(ModelAdmin):
    form = TranslatableModelForm

    @classmethod
    def translated_for_model(cls, model):
        fields = cls.fields
        for translations_model in model._parler_meta.get_all_models():
            for f_name in translations_model.get_translated_fields():
                if f_name not in fields:
                    continue

                names = [f[1] for f in _get_translated_fields_names(f_name)]
                fields = _replace_field(fields, f_name, names)

        form = cls.form
        if form is TranslatableModelForm:
            # TranslatableAdmin validation will not pass without form created
            # for specific model
            form = modelform_factory(model, form)

        attrs = {
            'fields': fields,
            'form': form,
        }
        return type(cls.__name__ + model.__name__ + 'Trans',
                    (cls, ), attrs)

    def get_available_languages(self, obj):
        """
        Fetching the available languages as queryset.
        """
        if obj:
            return obj.get_available_languages()
        else:
            return self.model._parler_meta.root_model.objects.none()

    def get_language_short_title(self, language_code):
        """
        Hook for allowing to change the title in the :func:`language_column` of
        the list_display.
        """
        return language_code

    def language_column(self, object):
        """
        The language column which can be included in the ``list_display``.
        """
        languages = self.get_available_languages(object)
        languages = [self.get_language_short_title(code) for code in languages]
        return '<span class="available-languages">{0}</span>'.format(
            ' '.join(languages))

    language_column.allow_tags = True
    language_column.short_description = _("Languages")
