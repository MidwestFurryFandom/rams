from . import *

@Session.model_mixin
class Attendee:
    comped_reason = Column(UnicodeText, default='', admin_only=True)