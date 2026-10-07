"""Date helpers shared by the scope transforms."""

import re

_DMY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_ISO = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def to_iso_date(value):
    """'30/9/2026' or '2026-09-30T10:00' -> '2026-09-30'.

    Regional sources publish DD/MM/YYYY; sorting those as text put 2017 votes
    first. Anything unparseable is returned unchanged.
    """
    text = str(value or "").strip()
    match = _DMY.match(text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    match = _ISO.match(text)
    if match:
        return match.group(1)
    return text
