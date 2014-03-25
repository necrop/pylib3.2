#-------------------------------------------------------------------------------
# Name: Decrufter
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

from regexcompiler import ReplacementListCompiler

top_markers = ("start of the project gutenberg",
               "start of this project gutenberg",
               "start of project gutenberg",
               "*end*the small print!",
               "*end the small print!",)
end_markers = ("end of the project gutenberg",
               "end of this project gutenberg",
               "end of project gutenberg",
               "end project gutenberg etext",)

cleaner = ReplacementListCompiler((
    (r"<\/?[a-z]{1,2>", ""),   # html tagging (e.g. <i>, </i>)
    (r"<[a-z]{1,2} ?\/>", ""), # html tagging (e.g. <br/>)
    (r"   +\d+$", ""),))       # verse line numbers


class Decrufter(object):
    """Remove Gutenberg header and tail text (licensing info etc.), and clean
    up a few other extraneous bits of cruft (line numbering, etc.).
    """

    def __init__(self):
        self.raw_lines = []

    def load_lines(self, lines):
        self.raw_lines = lines
        self.q1 = len(lines) / 4
        self.q3 = self.q1 * 3

    def decruft(self):
        cruft_lines = []
        for i, l in enumerate(self.raw_lines):
            if ("project gutenberg" in l.lower() or
                "public domain etext" in l.lower() or
                "restrictions in how the file may be used" in l.lower()):
                cruft_lines.append(i)

        # Check if any of the cruft lines are between q1 and q3;
        # raise alarm if so.
        # (This should only happen with very short texts, relative to
        # the amount of cruft; these need to be handled differently.)
        alarm = False
        for i in cruft_lines:
            if i > self.q1 and i < self.q3:
                alarm = True
                break

        top, bottom = (0, 0)
        if cruft_lines and not alarm:
            for i in cruft_lines:
                if i < self.q1:
                    top = i + 1
                if i > self.q3 and not bottom:
                    bottom = i
        else:
            for i, l in enumerate(self.raw_lines):
                l_lower = l.lower()
                if i < len(self.raw_lines) - 30:
                    for m in top_markers:
                        if m in l_lower:
                            top = i + 1
                if i > 30:
                    for m in end_markers:
                        if m in l_lower:
                            bottom = i

        if bottom:
            lines_new = self.raw_lines[top:bottom]
        else:
            lines_new = self.raw_lines[top:]
        return [clean_line(l) for l in lines_new]


def clean_line(l):
    l = l.replace(u"\x60\x60", "\"")
    l = l.replace("\'\'", "\"")
    l = cleaner.edit(l)
    return l
