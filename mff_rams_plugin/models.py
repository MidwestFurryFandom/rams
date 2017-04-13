from . import *

@Session.model_mixin
class Group:
    power = Column(Integer, default=0)

    @cost_property
    def power_cost(self):
        return c.POWER_PRICE * self.power

@Session.model_mixin
class Attendee:
    comped_reason = Column(UnicodeText, default='', admin_only=True)