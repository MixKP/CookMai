import re
from abc import ABC, abstractmethod


class CategoryValidator(ABC):
    @abstractmethod
    def is_valid(self, category):
        pass


class TimeKeywordValidator(CategoryValidator):
    def __init__(self, keywords):
        self.keywords = keywords

    def is_valid(self, category):
        category_str = str(category).lower().strip()
        return not any(keyword in category_str for keyword in self.keywords)


class DigitStartValidator(CategoryValidator):
    def is_valid(self, category):
        category_str = str(category).lower().strip()
        if not category_str or category_str[0].isdigit():
            return False
        return True


class OnlyDigitsValidator(CategoryValidator):
    def is_valid(self, category):
        category_str = str(category).lower().strip()
        return not re.match(r'^[\d\s]+$', category_str)


class CompositeValidator(CategoryValidator):
    def __init__(self, validators):
        self.validators = validators

    def is_valid(self, category):
        return all(validator.is_valid(category) for validator in self.validators)


class CategoryValidatorFactory:
    @staticmethod
    def create_default_validator():
        time_keywords = ['min', 'mins', 'minute', 'minutes', 'hr', 'hrs', 'hour', 'hours',
                       'less', 'under', 'over', 'more', 'within', '<', '>', '≤', '≥']

        validators = [
            DigitStartValidator(),
            OnlyDigitsValidator(),
            TimeKeywordValidator(time_keywords)
        ]
        return CompositeValidator(validators)
