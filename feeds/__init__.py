"""The general feed builder.

A feed is a literal answer to the question "what types of posts do you want to
see?" — no decoding, no shared vocabulary. The answer is the criteria the
quality check judges against. The pool of search terms is planted once, from
the answer, when the feed is created (harvest.py); the crawler then works it
continuously — judging posts (judge.py) and loading the ones that fit onto the
feed. Keyword harvesting and post judgement are separate processes on purpose:
harvesting runs only at feed creation, judging runs on every crawl. Each feed
is self-contained in one record. See request.py, crawl.py, judge.py and
harvest.py.
"""
