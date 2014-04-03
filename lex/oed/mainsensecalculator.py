
def calculate_main_sense(block):
    # Determine whether this block is revised or not (which matters
    #  if we have to do weighted-size calculations)
    try:
        revised = block.is_revised
    except AttributeError:
        revised = True

    primary_s2_senses = _find_primary_s2_senses(block)

    # Share out quotes, which then means we have to recalculate
    # first and last dates for each sense
    block.share_quotations()
    senses = _recalculate_dates(block.senses())

    for i, sense in enumerate(senses):
        # Number each sense by dictionary order (so we can retrieve the
        # original order)
        sense.dict_order = i
        # Count (adjusted) quotes in each sense - use as a proxy score
        sense.qcount = len(sense.thinned_year_list(revised=revised))
        sense.marked = False
    senses = _downscore_extended_uses(senses)
    senses = _downscore_supplement_senses(senses, revised)
    num_quotations = sum([s.qcount for s in senses])

    # Remove senses whose lemma does not match the entry headword
    senses_filtered = _remove_nonmatching_senses(senses)

    # Find all the non-obsolete senses
    senses_filtered = _remove_obsolete_senses(senses_filtered, revised)

    # Remove absol and attrib uses (unless this is the first sense)
    senses_filtered = _remove_attrib(senses_filtered,
                                     block.primary_wordclass().penn)

    # Remove minor senses to leave large senses only
    large_senses = _remove_minor_senses(senses_filtered)
    large_senses = _remove_low_grade_senses(large_senses, primary_s2_senses)

    ranking = []
    if len(senses_filtered) == 1:
        ranking = [senses_filtered[0], ]

    if not ranking:
        # Check if any of the remaining senses are explicitly indicated as
        #  the current sense
        for sense in senses_filtered:
            if sense.has_current_sense_indicator():
                sense.marked = True
                marked_main_sense = sense
                break
        else:
            marked_main_sense = None

        # Sort by date, and trim to the first 10
        large_senses.sort(key=_floordate)
        large_senses_trimmed = large_senses[0:10]
        # Restore original order
        large_senses_trimmed.sort(key=lambda s: s.dict_order)

        ranking = _compute_from_raw_values(large_senses_trimmed,
                                           marked_main_sense,
                                           revised)

    # Fall back on the first available sense, if any.
    if not ranking:
        ranking = large_senses[0:3] or senses_filtered[0:3] or senses[0:3]

    return ranking, len(senses_filtered), len(large_senses), num_quotations


def _remove_nonmatching_senses(senses):
    senses = [s for s in senses if not s.has_phrasal_indicator()]
    return [s for s in senses if
            not s.is_in_lemsect() and
            s.lemma_matches_headword(loose=True)]


def _remove_obsolete_senses(senses, revised):
    if revised:
        senses = [s for s in senses if
                  not s.is_marked_obsolete() and
                  s.end > 1970]
    else:
        senses = [s for s in senses if
                  not s.is_marked_obsolete() and
                  s.end > 1830]
    return senses


def _remove_attrib(senses, wordclass):
    return [s for s in senses if s.primary_wordclass().penn == wordclass
            and not s.is_grammatically_atypical()]


def _downscore_extended_uses(senses):
    """
    If a sense is figurative, extended, proverbial, etc., we downscore it -2.
    """
    for sense in senses:
        if sense.is_figurative():
            sense.qcount -= 2
    return senses


def _downscore_supplement_senses(senses, revised):
    """
    If a sense is unrevised, but has post-1950 quotes, it's probably been
    stuffed with quotations from the supplement. So we downscore it -2.
    """
    if not revised:
        for sense in senses:
            if sense.is_supplement_sense():
                sense.qcount -= 2
    return senses


def _remove_minor_senses(senses):
    # Remove senses with 'now rare' etc.
    large_senses = [s for s in senses if not s.has_rare_indicator()]

    # Remove below-average size senses
    if len(large_senses) >= 3:
        ave = sum([s.qcount for s in large_senses]) / len(large_senses)
        if ave >= 3:
            large_senses = [s for s in large_senses if s.qcount >= ave]

    return large_senses


def _remove_low_grade_senses(senses, primary_s2_senses):
    # Remove senses low down the hierarchy (high sense numbers, etc.)
    def _has_low_sense_number(s):
        if (s.s4_number() <= 5 and
                s.s7_number() <= 1 and
                s.s6_number() <= 3 and
                (s.s4_number() <= 3 or s.s6_number() <= 1)):
            return True
        else:
            return False

    return [s for s in senses if _has_low_sense_number(s)
            or s.node_id() in primary_s2_senses]


def _compute_from_raw_values(senses, marked_main_sense, revised):
    # Find the largest sense
    senses_sorted = senses[:]
    senses_sorted.sort(key=_floordate)
    senses_sorted.sort(key=lambda s: s.qcount, reverse=True)

    if marked_main_sense:
        winner = marked_main_sense
    elif not senses:
        winner = None
    # If the first remaining sense is reasonably substantial,
    #  we'll use that (even if other senses may be even larger)
    elif (senses[0].qcount > 8 and senses[0].end > 1970 and
            senses[0].qcount >= senses_sorted[0].qcount - 2):
        winner = senses[0]
    elif (not revised and senses[0].qcount > 7 and senses[0].end > 1870 and
            senses[0].qcount >= senses_sorted[0].qcount - 2):
        winner = senses[0]
    else:
        winner = None

    if senses_sorted and not winner:
        winner = senses_sorted[0]

    if not winner:
        return []
    else:
        senses_remaining = [s for s in senses_sorted if not s is winner]
        senses = [winner, ] + senses_remaining
        return senses


def _floordate(sense):
    year = max([sense.start, 1150])
    if year <= 1500:
        year = (year // 50) * 50
    elif year <= 1900:
        year = (year // 20) * 20
    else:
        year = (year // 10) * 10
    return year


def _recalculate_dates(senses):
    for s in senses:
        quotes = [q for q in s.quotations() if not q.is_suppressed()
                  and not q.is_bracketed()]
        quotes.sort(key=lambda q: q.year())
        if quotes:
            s.start = quotes[0].year()
            s.end = quotes[-1].year()
        else:
            s.start = s.date().start
            s.end = s.date().end
    return senses


def _find_primary_s2_senses(block):
    """
    Memorize the IDs of all senses that are among the first two senses
    of their <s2> block (for entries which have <s2> blocks).

    This is used to make sure that these senses are kept in contention
    as a possible main sense, even if they are a long way down the entry.
    """
    primaries = set()
    s2_blocks = block.s2blocks()
    if len(s2_blocks) > 1:
        for s2_block in s2_blocks:
            senses = s2_block.senses()[0:2]
            for sense in senses:
                primaries.add(sense.node_id())
    return primaries
