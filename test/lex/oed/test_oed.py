import os
import unittest
from lex.entryiterator import EntryIterator

FIXTURE_DIR = os.path.dirname(os.path.abspath(__file__))


class TestOed(unittest.TestCase):

    """
    Unit tests for OED libraries
    """

    entries = {}

    def setUp(self):
        iterator = EntryIterator(path=FIXTURE_DIR,
                                 dictType='oed',
                                 verbosity=None,
                                 fixLigatures=True,)
        self.entries = {int(e.id): e for e in iterator.iterate()}

    def tearDown(self):
        del self.entries

    def test_revised(self):
        """
        Test Entry.is_revised
        """
        for id, status in (
            (156796, 'revised'),
            (156790, 'revised'),
            (100461, 'unrevised'),
            (100453, 'unrevised'),
        ):
            entry = self.entries[id]
            if status == 'revised':
                self.assertTrue(entry.is_revised)
            else:
                self.assertFalse(entry.is_revised)

    def test_headwords(self):
        """
        Test Entry.headwords()
        """
        for id, count in (
            (100464, 1),
            (100460, 2),
            (100506, 2),
        ):
            entry = self.entries[id]
            self.assertEqual(len(entry.headwords()), count)

    def test_label(self):
        """
        Test Entry.label()
        """
        for id, label, label_tagged in (
            (100453, 'jaal-goat, n.', 'jaal-goat, n.'),
            (100463, 'jabble, v./1', 'jabble, v.<sup>1</sup>'),
            (100464, 'jabble, v./2', 'jabble, v.<sup>2</sup>'),
            (100460, 'jabbers | jabers, n.', 'jabbers | jabers, n.'),
            (100515, 'jacketed, adj.', 'jacketed, adj.'),
            (156796, 'quite, adv., adj., and int.', 'quite, adv., adj., and int.'),
        ):
            entry = self.entries[id]
            self.assertEqual(entry.label(), label)
            self.assertEqual(entry.label(tagged=True), label_tagged)

    def test_lemma(self):
        """
        Test Entry.lemma
        """
        for id, lemma in (
            (100453, 'jaal-goat'),
            (100463, 'jabble'),
            (100464, 'jabble'),
            (100460, 'jabbers'),
            (100515, 'jacketed'),
            (156796, 'quite'),
        ):
            entry = self.entries[id]
            self.assertEqual(entry.lemma, lemma)

    def test_header(self):
        """
        Test Entry.header()
        """
        for id, header in (
            (100455, 'colloq. or dial.'),
            (100459, 'rare.'),
            (100462, 'Sc.'),
            (100463, None),
        ):
            entry = self.entries[id]
            self.assertEqual(entry.header(), header)

    def test_senses(self):
        """
        Test Entry.senses()
        """
        for id, num_senses in (
            (100453, 1),
            (100455, 6),
            (100457, 5),
        ):
            entry = self.entries[id]
            self.assertEqual(len(entry.senses()), num_senses)

    def test_senses(self):
        """
        Test Entry.revsect_senses() and Entry.lemsect_senses()
        """
        for id, num_senses, num_revsect_senses, num_lemsect_senses in (
            (100453, 1, 0, 0),
            (100455, 6, 0, 1),
            (100457, 5, 0, 2),
            (100485, 178, 1, 111),
        ):
            entry = self.entries[id]
            self.assertEqual(len(entry.senses()), num_senses, _msg(entry))
            self.assertEqual(len(entry.lemsect_senses()), num_lemsect_senses, _msg(entry))
            self.assertEqual(len(entry.revsect_senses()), num_revsect_senses, _msg(entry))

    def test_sense_coherence(self):
        """
        Test that sense subcategories add up to Entry.senses()
        """
        for id, entry in self.entries.items():
            sum_senses = (len(entry.lemsect_senses()) +
                          len(entry.revsect_senses()) +
                          len(entry.sensesect_senses()))
            self.assertEqual(len(entry.senses()), sum_senses, _msg(entry))


def _msg(entry):
    return '%s -- %s' % (entry.id, entry.label())


if __name__ == "__main__":
    unittest.main()
