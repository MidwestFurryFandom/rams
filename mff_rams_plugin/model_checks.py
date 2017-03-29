from . import *

@validation.Attendee
def need_comped_reason(attendee):
    if attendee.paid == c.NEED_NOT_PAY and not attendee.comped_reason:
        return 'You must enter a reason for comping this attendee\'s badge.'