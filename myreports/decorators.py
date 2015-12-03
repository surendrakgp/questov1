from functools import partial

from universal.decorators import not_found_when

restrict_to_staff = partial(
    not_found_when,
    condition=lambda req: not req.user.is_staff,
    feature="MyReports",
    message="Feature currently restricted to DirectEmployers staff.")
