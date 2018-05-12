import re

from uber.decorators import prereg_validation, validation
from uber.config import c
from uber.model_checks import ignore_unassigned_and_placeholders


@validation.Attendee
def need_comped_reason(attendee):
    if attendee.paid == c.NEED_NOT_PAY and not attendee.comped_reason:
        return 'You must enter a reason for comping this attendee\'s badge.'


@validation.Attendee
@validation.Group
def no_emojis(model):
    for column in model.__table__.columns:
        emojis = re.compile(
            r'([\U0000231A-\U0000231B]|[\U000023E9-\U000023EC]|\U000023F0'
            r'|\U000023F3|[\U000025FD-\U000025FE]|[\U00002614-\U00002615]'
            r'|[\U00002648-\U00002653]|\U0000267F|\U00002693|\U000026A1'
            r'|[\U000026AA-\U000026AB]|[\U000026BD-\U000026BE]'
            r'|[\U000026C4-\U000026C5]|\U000026CE|\U000026D4|\U000026EA'
            r'|[\U000026F2-\U000026F3]|\U000026F5|\U000026FA|\U000026FD'
            r'|\U00002705|[\U0000270A-\U0000270B]|\U00002728|\U0000274C'
            r'|\U0000274E|[\U00002753-\U00002755]|\U00002757'
            r'|[\U00002795-\U00002797]|\U000027B0|\U000027BF'
            r'|[\U00002B1B-\U00002B1C]|\U00002B50|\U00002B55|\U0001F004'
            r'|\U0001F0CF|\U0001F18E|[\U0001F191-\U0001F19A]|\U0001F201'
            r'|\U0001F21A|\U0001F22F|[\U0001F232-\U0001F236]'
            r'|[\U0001F238-\U0001F23A]|[\U0001F250-\U0001F251]'
            r'|[\U0001F300-\U0001F320]|[\U0001F32D-\U0001F335]'
            r'|[\U0001F337-\U0001F37C]|[\U0001F37E-\U0001F393]'
            r'|[\U0001F3A0-\U0001F3CA]|[\U0001F3CF-\U0001F3D3]'
            r'|[\U0001F3E0-\U0001F3F0]|\U0001F3F4|[\U0001F3F8-\U0001F43E]'
            r'|\U0001F440|[\U0001F442-\U0001F4FC]|[\U0001F4FF-\U0001F53D]'
            r'|[\U0001F54B-\U0001F54E]|[\U0001F550-\U0001F567]'
            r'|[\U0001F595-\U0001F596]|[\U0001F5FB-\U0001F64F]'
            r'|[\U0001F680-\U0001F6C5]|\U0001F6CC|\U0001F6D0'
            r'|[\U0001F6EB-\U0001F6EC]|[\U0001F910-\U0001F918]'
            r'|[\U0001F980-\U0001F984]|\U0001F9C0'
            r'|[\U0001F1E6-\U0001F1FC][\U0001F1E6-\U0001F1FF])')
        if re.search(emojis, str(getattr(model, column.name))):
            return 'Fields cannot contain emoji'


@validation.Attendee
@ignore_unassigned_and_placeholders
def badge_printed_name(attendee):
    if not attendee.badge_printed_name:
        return 'Please enter a name for your custom-printed badge.'


@prereg_validation.Group
def dealer_wares(group):
    pass


@prereg_validation.Group
def dealer_description(group):
    if group.tables and not group.description:
        return 'Please provide a description for us to evaluate ' \
               'your submission and use in listings.'


@prereg_validation.Group
def power_usage(group):
    if group.power and not group.power_usage:
        return 'Please provide a list of what powered devices you ' \
               'expect to use.'
