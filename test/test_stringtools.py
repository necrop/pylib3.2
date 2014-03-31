import unittest
import stringtools


class TestStringtools(unittest.TestCase):

    """
    Unit tests for stringtools
    """

    test_texts = (
        ('apple', 'apple', 'apple',),
        ('ApplE', 'ApplE', 'apple',),
        ('Café', 'Cafe', 'cafe',),
        ('NAÏVE', 'NAIVE', 'naive',),
        ('N_A_Ï_V E', 'N_A_I_V E', 'naive',),
        ('-PRE-eminent  ', '-PRE-eminent  ', 'preeminent',),
    )
    prefix_tests = (
        ('mouse', 2, 'mo'),
        ('...happiness,', 4, 'happ'),
        ('DOOR', 2, 'do'),
    )
    suffix_tests = (
        ('mouse', 2, 'se'),
        ('happiness,', 4, 'ness'),
        ('DOOR-KNOB', 3, 'nob'),
    )

    def test_asciify(self):
        """
        Test stringtools.asciify()
        """
        for source, result, _ in self.test_texts:
            self.assertEqual(stringtools.asciify(source), result)

    def text_lexical_sort(self):
        """
        Test stringtools.lexical_sort()
        """
        for source, _, result in self.test_texts:
            self.assertEqual(stringtools.lexical_sort(source), result)

    def test_prefix(self):
        """
        Test stringtools.prefix()
        """
        for source, num, result in self.prefix_tests:
            self.assertEqual(stringtools.prefix(source, num), result)

    def test_suffix(self):
        """
        Test stringtools.suffix()
        """
        for source, num, result in self.suffix_tests:
            self.assertEqual(stringtools.suffix(source, num), result)




if __name__ == "__main__":
    unittest.main()
