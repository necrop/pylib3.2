import re
from bs4 import BeautifulSoup


def fillet_file(in_file, out_file):
    paras = parse_html(in_file)
    with open(out_file, 'w') as filehandle:
        for para in paras:
            filehandle.write(para)
            filehandle.write('\n\n')


def parse_html(filepath):
    with open(filepath) as filehandle:
        doc = ''.join(filehandle.readlines())

    soup = BeautifulSoup(doc)
    html_paras = soup.find_all('p')
    paras = []
    for para in html_paras:
        text = ' '.join(para.stripped_strings)
        paras.append(text)

    #-------------------------------------------
    # Clean out metatext from the start and end
    #-------------------------------------------
    # Find metatext indicators
    metatext_indices = []
    for i, text in enumerate(paras):
        if ('PROJECT GUTENBERG' in text or
                'end the small print!' in text.lower()):
            metatext_indices.append(i)
    # Find the last index in the first 10%,
    start_index, end_index = 0, len(paras)
    matched = False
    for buffer in (.1, .2, .3):
        for index in metatext_indices:
            if index < len(paras) * buffer:
                start_index = index
                matched = True
        if matched:
            break

    # ...and the first index in the last 10%
    matched = False
    for buffer in (.9, .8, .7):
        for index in metatext_indices:
            if index > len(paras) * buffer:
                end_index = index
                matched = True
                break
        if matched:
            break

    # Retain only the paragraphs between these start and end points
    paras = paras[start_index+1:end_index]

    #-------------------------------------------
    # Clean up the remaining paras
    #-------------------------------------------
    paras = [_cleanup_para(para) for para in paras]
    paras = [p for p in paras if p]

    return paras


def _cleanup_para(para):
    para = para.replace('\n', ' ')
    para = re.sub('  +', ' ', para)
    return para.strip()
