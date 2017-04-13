from . import *

@Session.model_mixin
class Group:
    power = Column(Integer, default=0)

    @cost_property
    def power_cost(self):
        return c.POWER_PRICE * self.power

    @property
    def dealer_badges_remaining(self):
        """
        This overrides a function in the main plugin which controls how many badges a Dealer group may purchase.
        We do not have any restrictions on dealer badges so this just returns an arbitrary number, allowing a Dealer
        to add up to that many badges at a time.
        :return:
        """
        return 10

    @presave_adjustment
    def dealers_add_badges(self):
        if self.is_dealer and self.is_new:
            self.can_add = True

@Session.model_mixin
class Attendee:
    comped_reason = Column(UnicodeText, default='', admin_only=True)