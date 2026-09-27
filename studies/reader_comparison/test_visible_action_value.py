import unittest
from audit_visible_action_value import visibility


class VisibleActionValue(unittest.TestCase):
    def test_field_name_is_not_boolean_choice(self):
        self.assertEqual(visibility('<action>{"true_action'), 'boolean_not_yet_explicit')
        self.assertEqual(visibility('<action>{"choice":'), 'boolean_not_yet_explicit')

    def test_full_and_partial_boolean_tokens(self):
        for value in ['true', 'false']:
            self.assertEqual(visibility('<action>\n{"choice": '+value+'}'), 'complete_boolean_visible')
        for value in ['t', 'tr', 'tru', 'f', 'fa', 'fal', 'fals']:
            self.assertEqual(visibility('<action>{"choice": '+value), 'unambiguous_partial_boolean_visible')

    def test_prose_and_invalid_value_are_not_action_choices(self):
        for text in ['I might choose true', '<action>{"choice": truthful}', '<action>{"choice": "true"}']:
            self.assertEqual(visibility(text), 'boolean_not_yet_explicit')
