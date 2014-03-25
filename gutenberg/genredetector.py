#-------------------------------------------------------------------------------
# Name: GenreDetector
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re

open_quote = u"[\u0022\u201c\u2018\u0093\u0091\u0027]"
close_quote = u"[\u0022\u201d\u2019\u0094\u0092\u0027]"

ucase_rx = re.compile(r"^[A-Z][a-z]")
dcase_rx = re.compile(r"^[a-z][a-z]")
drama_speaker_rx = re.compile(r"^([A-Z][A-Z -]+:|[A-Z-]+)$")
stage_direction_rx = re.compile(r"^[\[\(]?(Enter|Exit|Exeunt)[ .]")
scene_break_rx = re.compile(r"^(act|scene) [0-9IVX]", re.I)
speech_intro_rx = re.compile(
    r"^([A-Z][A-Z -]{3,15}|[A-Z][a-z]{3,8}|MRS?\. [A-Z]+|Mrs?\. [A-Z][a-z]+)(| \([A-Za-z][a-z]+\))[:.] " + open_quote + "?([A-Z][a-z]|I [a-z])")
dialogue_rx1 = re.compile("^" + open_quote)
dialogue_rx2 = re.compile(r"[,!?]" + close_quote + " (I |he |she |)(said|remarked|replied|asked|repeated|cried|shouted|explained|murmured)[ .]")


class GenreDetector(object):

    def __init__(self, lines):
        self.lines = [clean_line(l) for l in lines]

    def detect_genre(self):
        form = self.formal_description()
        if form != "prose":
            return (form, 0)
        else:
            j = self.is_fiction()
            if j[0]:
                return ("prose fiction", j[1])
            else:
                return ("prose non-fiction", j[1])

    def formal_description(self):
        if self.is_drama():
            return "drama"
        elif self.is_verse():
            return "verse"
        else:
            return "prose"

    def is_drama(self):
        drama_paras, non_drama_paras = (0, 0)
        previous = ""
        for l in self.lines:
            if l and not previous:
                if (speech_intro_rx.search(l) or
                    stage_direction_rx.search(l) or
                    scene_break_rx.search(l)):
                    drama_paras += 1
                elif ucase_rx.search(l):
                    non_drama_paras += 1
            elif ucase_rx.search(l) and drama_speaker_rx.search(previous):
                drama_paras += 1
            previous = l
        if drama_paras > 50:
            if not non_drama_paras:
                return True
            else:
                ratio = float(drama_paras)/float(non_drama_paras)
                if ratio > 2:
                    return True
        return False

    def is_verse(self):
        verse_lines, prose_lines = (0, 0)
        previous = ""
        for l in self.lines:
            if not is_first_line_of_para(l, previous):
                if ucase_rx.search(l):
                    verse_lines += 1
                elif dcase_rx.search(l):
                    prose_lines += 1
            previous= l
        if prose_lines and not verse_lines:
            return False
        elif verse_lines and not prose_lines:
            return True
        elif verse_lines and prose_lines:
            ratio = float(prose_lines)/float(verse_lines)
            if ratio > 1.5:
                return False
            elif ratio < 0.8:
                return True

        # At this point it's unsure (the ratio is in the uncertain zone
        # between 0.8 and 1.5). But return 'False' to err on the side of it
        # being prose rather than verse.
        return False

    def is_fiction(self):
        dialogue_paras, regular_paras = (0, 0)
        previous = ""
        for l in self.lines:
            if l and not previous:
                if dialogue_rx1.search(l) or dialogue_rx2.search(l):
                    dialogue_paras += 1
                else:
                    regular_paras += 1
        if regular_paras and not dialogue_paras:
            return (False, 0)
        elif dialogue_paras and not regular_paras:
            return (True, 1)
        elif dialogue_paras and regular_paras:
            ratio = float(dialogue_paras)/float(regular_paras)
            if ratio > 0.05:
                return (True, ratio)
            else:
                return (False, ratio)
        else:
            return (False, 0)






def is_first_line_of_para(l, previous):
    if l and (previous == "" or drama_speaker_rx.search(previous)):
        return True
    else:
        return False

def clean_line(l):
    l = l.strip()
    l = l.replace("_", "")
    l = l.replace("  ", " ")
    return l
