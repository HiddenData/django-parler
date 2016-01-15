from django.core.cache import cache
from django.conf import settings
from django.db.models import Manager
from .utils import AppTestCase
from .testapp.models import ManualModel, ManualModelTranslations, SimpleModel, Level1, Level2, ProxyBase, ProxyModel, DoubleModel, RegularModel, CharModel


JSON_BACKEND = settings.PARLER_BACKEND == 'json'


class ModelConstructionTests(AppTestCase):
    """
    Test model construction
    """
    def test_manual_model(self):
        """
        Test the metaclass of the model.
        """
        # Test whether the link has taken place
        self.assertIsInstance(ManualModel().translations, Manager)  # RelatedManager class
        # self.assertIs(ManualModel().translations.model, ManualModelTranslations)
        # self.assertIs(ManualModel._parler_meta.root_model, ManualModelTranslations)


    # def test_simple_model(self):
    #     """
    #     Test the simple model syntax.
    #     """
    #     self.assertIs(SimpleModel().translations.model, SimpleModel._parler_meta.root_model)


    def test_inherited_model(self):
        """
        Test the inherited model syntax.
        """
        # First level has 1 ParlerMeta object
        if JSON_BACKEND:
            l1_translations_name = 'l1_translations_data'
            l2_translations_name = 'l2_translations_data'
        else:
            l1_translations_name = 'l1_translations'
            l2_translations_name = 'l2_translations'

        self.assertEqual(Level1._parler_meta.root.translations_name, l1_translations_name)
        if not JSON_BACKEND:
            self.assertEqual(Level1._parler_meta.root.model.__name__, 'Level1Translation')
        self.assertEqual(len(Level1._parler_meta), 1)

        # Second level has 2 ParlerMeta objects.
        self.assertEqual(len(Level2._parler_meta), 2)
        self.assertEqual(Level2._parler_meta[0].translations_name, l1_translations_name)
        self.assertEqual(Level2._parler_meta[1].translations_name, l2_translations_name)
        if not JSON_BACKEND:
            self.assertEqual(Level2._parler_meta[1].model.__name__, 'Level2Translation')

        # Level 2 root attributes should point to the top-level object (Level1)
        if not JSON_BACKEND:
            self.assertEqual(Level2._parler_meta.root_model.__name__, 'Level1Translation')
        self.assertEqual(Level2._parler_meta.root_translations_name, l1_translations_name)
        self.assertEqual(Level2._parler_meta.root, Level1._parler_meta.root)


    def test_proxy_model(self):
        """
        Test whether proxy models can get new translations
        """
        if JSON_BACKEND:
            base_translations_name = 'base_translations_data'
            proxy_translations_name = 'proxy_translations_data'
        else:
            base_translations_name = 'base_translations'
            proxy_translations_name = 'proxy_translations'
        # First level has 1 ParlerMeta object
        self.assertEqual(ProxyBase._parler_meta.root.translations_name, base_translations_name)
        self.assertEqual(len(ProxyBase._parler_meta), 1)

        # Second level has 2 ParlerMeta objects
        self.assertEqual(len(ProxyModel._parler_meta), 2)
        self.assertEqual(ProxyModel._parler_meta[0].translations_name, base_translations_name)
        self.assertEqual(ProxyModel._parler_meta[1].translations_name, proxy_translations_name)

        if not JSON_BACKEND:
            self.assertEqual(ProxyModel._parler_meta[0].model.__name__, 'ProxyBaseTranslation')
            self.assertEqual(ProxyModel._parler_meta[1].model.__name__, 'ProxyModelTranslation')

        # Second inheritance level attributes should point to the top-level object (ProxyBase)
        if not JSON_BACKEND:
            self.assertEqual(ProxyModel._parler_meta.root_model.__name__, 'ProxyBaseTranslation')
        self.assertEqual(ProxyModel._parler_meta.root_translations_name, base_translations_name)
        self.assertEqual(ProxyModel._parler_meta.root, ProxyBase._parler_meta.root)


    def test_double_translation_table(self):
        """
        Test how assigning two translation tables works.
        """
        self.assertIsNone(DoubleModel._parler_meta.base)  # Should call .add_meta() instead of overwriting/chaining it.
        self.assertEqual(len(DoubleModel._parler_meta), 2)
        # self.assertEqual(DoubleModel._parler_meta[0].translations_name, "base_translations")
        # self.assertEqual(DoubleModel._parler_meta[1].translations_name, "more_translations")


    def test_overlapping_proxy_model(self):
        """
        Test the simple model syntax.
        """
        from parler.tests.testapp.invalid_models import RegularModelProxy

        # Create an object without translations
        RegularModel.objects.create(id=98, original_field='untranslated')
        self.assertEqual(RegularModelProxy.objects.count(), 1)

        # Refetch from db, should raise an error.
        self.assertRaises(RuntimeError, lambda: RegularModelProxy.objects.all()[0])


    def test_model_with_different_pks(self):
        """
        Test that TranslatableModels works with different types of pks
        """
        self.assertIsInstance(SimpleModel.objects.create(tr_title='Test'), SimpleModel)
        self.assertIsInstance(CharModel.objects.create(pk='test', tr_title='Test'), CharModel)
