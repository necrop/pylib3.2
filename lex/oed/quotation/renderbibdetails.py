
from lxml import etree

from regexcompiler import ReplacementListCompiler

# Regex sequences used for rendering citation as HTML or plain-text
DETAGGER = ReplacementListCompiler((
    (r'<([a-zA-Z]+) [^<>]*/>', r'<\1/>'),  # strip attributes
    (r'<([a-zA-Z]+) [^<>]*>', r'<\1>'),    # to make life easier
    (r'<([a-zA-Z])', r' <\1'),
    (r'<(tt|dp|edn|ms|place|ob)>', '('),
    (r'</(tt|dp|edn|ms|place|ob)>', ')'),
    (r'<vma>', r'_+BOLD_'),
    (r'</vma>', r'_-BOLD_'),
    (r'<w>', r'_+CITE_'),
    (r'</w>', r'_-CITE_'),
    (r'</a> *<a>', r'</a> & <a>'),
    (r'<(a|pt)>', r'_+SC_'),
    (r'</(a|pt)>', r'_-SC_'),
    (r'<tr>', ' tr. '),
    # Remove all remaining tags
    (r'<[^<>]*>', ''),
))
HTMLIFIER = ReplacementListCompiler((
    (r'_\+BOLD_', r'<strong>'),
    (r'_-BOLD_', r'</strong>'),
    (r'_\+CITE_', r'<cite>'),
    (r'_-CITE_', r'</cite>'),
    (r'_\+SC_', r'<span style="font-variant: small-caps">'),
    (r'_-SC_', r'</span>'),
    (r'& ', r'&amp; '),
    (r'  +', ' '),
))
HTMLIFIER_LITE = ReplacementListCompiler((
    (r'_\+BOLD_', r'<b>'),
    (r'_-BOLD_', r'</b>'),
    (r'_\+CITE_', r'<i>'),
    (r'_-CITE_', r'</i>'),
    (r'_\+SC_', r'<sc>'),
    (r'_-SC_', r'</sc>'),
    (r'& ', r'&amp; '),
    (r'  +', ' '),
))
PLAINTEXTIFIER = ReplacementListCompiler((
    (r'_\+BOLD_', ''),
    (r'_-BOLD_', ''),
    (r'_\+CITE_', r'_'),
    (r'_-CITE_', r'_'),
    (r'_\+SC_', ''),
    (r'_-SC_', ''),
    (r'&amp;', r'&'),
    (r'  +', ' '),
))


def renderbibdetails(node, method):
    serialized = etree.tounicode(node)
    serialized = DETAGGER.edit(serialized)
    if method == 'html':
        serialized = HTMLIFIER.edit(serialized)
    elif method == 'html_lite':
        serialized = HTMLIFIER_LITE.edit(serialized)
    else:
        serialized = PLAINTEXTIFIER.edit(serialized)
    return serialized.strip(' ,')
