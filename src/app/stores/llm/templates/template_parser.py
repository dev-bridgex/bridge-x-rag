import os
from app.logging import get_logger

logger = get_logger(__name__)

class TemplateParser:

    def __init__(self, language: str=None, default_language='en'):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
        self.language = None

        self.set_language(language)


    def set_language(self, language: str):
        if not language:
            self.language = self.default_language

        language_path = os.path.join(self.current_path, "locales", language)
        if os.path.exists(language_path):
            self.language = language
        else:
            self.language = self.default_language

    def get(self, group: str, key: str, vars: dict={}):
        if not group or not key:
            return None

        group_path = os.path.join(self.current_path, "locales", self.language, f"{group}.py" )
        targeted_language = self.language
        if not os.path.exists(group_path):
            group_path = os.path.join(self.current_path, "locales", self.default_language, f"{group}.py" )
            targeted_language = self.default_language

        if not os.path.exists(group_path):
            return None

        # import group module
        module = __import__(f"app.stores.llm.templates.locales.{targeted_language}.{group}", fromlist=[group])

        if not module:
            return None

        key_attribute = getattr(module, key)
        return key_attribute.substitute(vars)

    def get_template(self, group: str, key: str, vars: dict={}):
        """Alias for get() method to maintain compatibility with code that uses get_template"""
        try:
            return self.get(group, key, vars)
        except Exception as e:
            logger.error(f"Error getting template {group}/{key}: {str(e)}")
            return ""
