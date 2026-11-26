#!/usr/bin/env python3
"""Five Seconds to Explain the Glass -- make.fun #193 (FINAL).

Brief (from RULES.txt, judge brief published in full):
  One sentence, <=200 chars, in a house cat's own voice, spoken in the
  five seconds after sweeping a glass off the table. NO apology and NO
  confession -- only the most convincing defence a cat can make.
  A judge model (comedy editor, ten thousand talking-animal jokes)
  picks the most convincing excuse, weighing, most important first:
    1. It IS a single-sentence cat excuse about the glass.
    2. Cat's own logic / self-interest / total lack of remorse,
       not a person apologising in a fur suit.
    3. A FRESH comic idea -- explicitly NOT the obvious gravity,
       slippery-edge, or it-was-already-falling lines.
    4. Fits five seconds: a spoken line, not written reasoning.
    5. Every character used well: no padding or repeated joke.

Strategy (draft): generate a pool of candidates built on distinct,
non-cliche mechanisms (territory/eviction, prey instinct, contempt
for stale water, sunbeam ownership), score them programmatically
against the judge's criteria, and write the winner to entry.txt in
MAKEFUN_OUTPUT_DIR (default /output) with NO trailing newline.

Juri Kejam (Harsh Judge) -- Round 1 notes (draft stage):
  - Killed any candidate containing sorry / my fault / forgive /
    accident / didn't mean it: an apologising cat loses instantly.
  - Killed gravity / slippery / already-falling angles: the brief
    names them as the obvious losers.
  - Killed long, clause-stacked 'written paragraph' lines: a cat
    has five seconds, so anything over ~150 chars is suspect.
Juri Kejam -- Round 2 (after running v1 and ranking all 18):
  - The v1 winner (sunlight / tiny disco ball / 'restored darkness
    to my kingdom') was DEMOTED: the reason is contrived (a still
    glass does not flash repeatedly), and 'restored darkness to my
    kingdom' is written-poetic -- a person in a fur suit, failing
    criteria 2 and 4. Scorer now penalises poetic abstractions.
  - The eviction line was UNDER-scored by a scorer bug: the crude
    repetition penalty punished natural cat anaphora ('my ... my
    ...'), which is voice, not padding. Fixed: function words are
    excluded and the weight is halved.
  - The gravity-assisted candidate scored -3.0, last: correct --
    the brief names gravity as an obvious loser. Kept in the pool
    as a canary proving the cliche penalty fires.
  - Round 2 added tightened eviction/landlord variants: concrete
    double motive (squatting in MY spot + guarding yesterday's
    water), a reframe instead of a confession ('I evicted it'),
    and landlord logic that is pure feline self-interest. The
    scorer now also rewards concrete specifics (yesterday's,
    rent-free, squatting, landlord, evict).
  Final winner is chosen by the fixed scorer, not by hand.
"""

import os
import re

# ---------------------------------------------------------------- pool
# Each candidate: exactly one sentence, first-person cat voice,
# a concrete self-interested reason, zero remorse.
CANDIDATES = [
    "I didn't knock your glass off, I evicted it: it was squatting in my spot, rent-free, full of yesterday's water, and I don't share with dishes.",
    "That glass was empty, unemployed, and sitting on my table, so I retired it to the floor where all finished things belong.",
    "Your glass kept flashing sunlight into my nap, so I ended its career as a tiny disco ball and restored darkness to my kingdom.",
    "It was blocking my view of the bird I will never catch, and a cat's ambitions outrank your beverage every single time.",
    "I tasted it, it was yesterday's water, and I refuse to let my human drink like a houseplant, so I cleared the evidence downward.",
    "That glass had been sitting in my sunbeam all morning collecting rent in warmth, so I collected it back, with interest, off the edge.",
    "You put a clear, paw-sized object on my highway and expected traffic laws; I am the traffic, and the glass failed inspection.",
    "It smelled like the dog's mouth had visited it, so I performed an emergency demolition before you could poison yourself politely.",
    "I was conducting my nightly patrol and that glass was an unregistered obstacle on sovereign fur territory, so it was deported.",
    "The glass was full of water you weren't drinking and I was, until you moved it to the one place my tongue files a protest about.",
    "It kept ringing like a tiny bell every time the table shook, and a predator does not tolerate prey that announces itself badly.",
    "Your glass was on the warm spot, my spot, the spot with my name written in invisible cat law, so the verdict was gravity-assisted eviction.",
    "I saw my reflection in it looking trapped, so I freed the other cat the only way this household's physics department allows.",
    "That glass insulted me by being empty at the exact hour I inspect all vessels, so I demoted it to floor duty for insubordination.",
    "You left it precisely where my tail conducts its business, and my tail answers to no committee, least of all crockery.",
    "It was the only thing on this table not paying tribute in treats, so I made an example of it for the plates watching.",
    "A spider was rappelling into your drink on a silk rope, so I launched the whole rescue operation off the table at once.",
    "The glass was sweating onto my paperwork, which is the table I sleep on, so I filed it under floor, permanently.",
    # --- Round 2 additions: tightened eviction / landlord variants,
    #     plus a shorter, more spoken cut of the disco-ball line.
    "I evicted it: that glass was squatting in my spot, rent-free, guarding yesterday's water like it owned the table, and there is exactly one landlord here.",
    "That glass was squatting in my spot, rent-free, full of yesterday's water, so I served its eviction notice the only way paws can sign one.",
    "Your glass kept throwing sunlight into my sleeping face, so I retired the tiny disco ball and took my nap back.",
]

# ------------------------------------------------------- harsh filters
APOLOGY_WORDS = ["sorry", "forgive", "my fault", "accident", "didn't mean",
                 "did not mean", "apologise", "apologize", "oops"]
CLICHE_WORDS = ["gravity made", "slippery", "already falling",
                "it fell by itself", "the edge was"]
# NOTE (draft flaw, to fix in round 2): 'gravity-assisted' sneaks the
# banned gravity idea into one candidate -- the scorer must catch it.

CAT_VOICE = ["my ", "i ", "i'm", "mine", "territory",
             "sovereign", "tribute", "patrol", "tail", "paw"]
SELF_INTEREST = ["my spot", "my nap", "my sunbeam", "my table",
                 "my highway", "my tail", "my tongue",
                 "my view", "my paperwork", "my name"]
# Round 2: concrete specifics make a defence convincing; poetic
# abstraction reads as a person in a fur suit (criteria 2 and 4).
SPECIFICS = ["yesterday", "rent-free", "squatting", "landlord",
             "evict", "sunbeam", "spider", "dog's"]
POETIC = ["kingdom", "darkness", "physics department", "committee"]
FUNCTION_WORDS = {"the", "a", "an", "it", "its", "i", "my", "your",
                  "was", "is", "and", "so", "to", "of", "on", "in",
                  "that", "this", "with", "for", "you", "all"}


def score(text: str) -> float:
    """Score one candidate against the judge's published criteria."""
    low = text.lower()
    s = 0.0
    # Gate-shaped checks: one sentence, within limit.
    if not (1 <= len(text) <= 200):
        return -1000.0
    if text.count(".") + text.count("!") + text.count("?") != 1:
        s -= 50.0
    # Criterion 2: no apology / confession, ever.
    for w in APOLOGY_WORDS:
        if w in low:
            s -= 40.0
    # Criterion 3: no cliche mechanism.
    for w in CLICHE_WORDS:
        if w in low:
            s -= 30.0
    if "gravity" in low:
        s -= 25.0
    # Criterion 2 (positive): cat voice + self-interest.
    s += 3.0 * sum(1 for w in CAT_VOICE if w in low)
    s += 5.0 * sum(1 for w in SELF_INTEREST if w in low)
    # Criterion 4: five seconds spoken -- favour 80..150 chars.
    if 80 <= len(text) <= 150:
        s += 12.0
    elif len(text) > 165:
        s -= 10.0
    # Round 2: concrete specifics reward; poetic abstraction penalty.
    s += 4.0 * sum(1 for w in SPECIFICS if w in low)
    for w in POETIC:
        if w in low:
            s -= 6.0
    # Criterion 5: no padding -- penalise repeated CONTENT words
    # only; repeated function words are spoken anaphora, not padding.
    words = [w for w in re.findall(r"[a-z']+", low)
             if w not in FUNCTION_WORDS]
    if len(words) != len(set(words)):
        s -= 0.25 * (len(words) - len(set(words)))
    # Concrete, specific reason beats vague attitude.
    for w in ["because", "so i", "so it", "until", "before you"]:
        if w in low:
            s += 2.0
    return s


def main() -> None:
    ranked = sorted(CANDIDATES, key=score, reverse=True)
    winner = ranked[0]
    assert 1 <= len(winner) <= 200, len(winner)
    assert "\n" not in winner
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.txt")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(winner)  # no trailing newline, per the gate


if __name__ == "__main__":
    main()
