"""The general feed builder.

A feed is a literal answer to the question "what types of posts do you want to
see?" — no decoding, no shared vocabulary. The answer is the criteria the
quality check judges against; keywords are planted from it and harvested by
the feed's own crank (judge.py); the posts that fit are shown. Each feed is
self-contained in one record. See request.py, crawl.py and judge.py.
"""
