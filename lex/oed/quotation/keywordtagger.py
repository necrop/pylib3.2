
import re
from lxml import etree

import stringtools


def tag_keyword(quotation, keyword):
    """
    Having identified the keyword within the quotation text (using
    KeywordFinder), mark the keyword by adding <kw> tags around it.
    """
    if keyword:
        serialized = etree.tounicode(quotation.text.node)
        qt_splitter = re.search(r'^(<qt(>| [^<>]*>))(.*)(</qt>)$', serialized)
        opentag = qt_splitter.group(1)
        text = ' ' + qt_splitter.group(3) + ' '
        closetag = qt_splitter.group(4)
        text_tagged = None

        keyword = _clean_brackets(keyword)
        keyword = keyword.replace('*', '.').replace('+', '.')
        keyword_flat = stringtools.lexical_sort(keyword)

        matches = None
        for m in ('([ (>])(' + keyword + ')([,;:!?)<. ])',
                  '(.)(' + keyword + ')([,;:!?)<. -])',
                  '([^a-zA-Z])(' + keyword + ')([^a-zA-Z])',
                  '([ (>-])(' + keyword + ')(.)',
                  '(.)(' + keyword + ')(.)'):
            matches = re.findall(m, text)
            if matches:
                break
        if matches:
            prec, match, following = matches[0]
            before = prec + match + following
            after = prec + '<kw>' + match + '</kw>' + following
            text_tagged = text.replace(before, after)

        if not text_tagged:
            text2 = re.sub(r'<([a-z]+) [^<>]*/>', r'<\1/>', text)
            text2 = re.sub(r'<([a-z]+) [^<>]*>', r'<\1>', text2)
            tokens = text2.split()
            for token in tokens:
                token2 = re.sub(r'<[^<>]+>', '', token)
                token2 = token2.strip(',:;!?.()')
                if token2 == keyword:
                    target = token.strip(',:;!?.()')
                    text_tagged = text2.replace(target, '<kw>' + target + '</kw>')
                    break

        if not text_tagged:
            for round in (1, 2):
                text2 = re.sub(r'<([a-z]+) [^<>]*/>', r'<\1/>', text)
                text2 = re.sub(r'<([a-z]+) [^<>]*>', r'<\1>', text2)

                # text_true is the version we'll actually be tagging
                #  - with ellipses, etc., still in place
                text_true = text2

                if round == 2:
                    # Replace ellipses and m-dashes with spaces, so that
                    # adjacent words get tokenized
                    for char in ('\u2025', '\u2026', '\u2014'):
                        text2 = text2.replace(char, ' ')

                # Tokenize and make into ngrams
                tokens = text2.split()
                ngrams = (_compile_ngrams(tokens, 1) +
                          _compile_ngrams(tokens, 2) +
                          _compile_ngrams(tokens, 3) +
                          _compile_ngrams(tokens, 4) +
                          _compile_ngrams(tokens, 5) +
                          _compile_ngrams(tokens, 6))

                target = None
                for ngram_full, ngram_flat in ngrams:
                    if keyword_flat == ngram_flat:
                        target = ngram_full
                        break
                if target:
                    # Strip ellipses and dashes
                    target = target.strip('\u2025\u2026\u2014')
                    text_tagged = text_true.replace(target, '<kw>' + target + '</kw>')
                    break

        if not text_tagged:
            keyword_tokens = keyword.split()
            if len(keyword_tokens) >= 2:
                first = re.findall(keyword_tokens[0], text)
                last = re.findall(keyword_tokens[-1], text)
                if len(first) == 1 and len(last) == 1:
                    pattern = ('(' + keyword_tokens[0] + '.*?' +
                               keyword_tokens[-1] + ')')
                    text_tagged = re.sub(pattern, r'<kw>\1</kw>', text)
                    #print('----------------------------------------------------')
                    #print(serialized)
                    #print('|' + keyword + '|')
                    #print(text_tagged)

        if text_tagged and '<kw>' in text_tagged:
            serialized_tagged = opentag + text_tagged.strip() + closetag
            try:
                node_tagged = etree.fromstring(serialized_tagged)
            except etree.XMLSyntaxError:
                pass
            else:
                parent = quotation.text.node.getparent()
                parent.replace(quotation.text.node, node_tagged)
        else:
            pass
            #print('----------------------------------------------------')
            #print(serialized)
            #print('|' + keyword + '|')






def _clean_brackets(text):
    for punc in ('(', ')', '[', ']'):
        text = text.replace(punc, '')
    return text


def _compile_ngrams(tokens, length):
    ngrams = []
    for i in range(0, len(tokens)):
        try:
            window = tokens[i:i+length]
        except IndexError:
            pass
        else:
            ngram = ' '.join(window)
            ngram = ngram.strip(',:;().!?- ')
            ngram_flat = re.sub(r'<[^<>]+>', '', ngram)
            ngram_flat = stringtools.lexical_sort(ngram_flat)

            ngrams.append((ngram, ngram_flat))
    return ngrams
