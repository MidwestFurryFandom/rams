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

    @cost_property
    def badge_cost(self):
        registered = self.registered_local if self.registered else None
        if self.paid == c.NEED_NOT_PAY:
            return 0
        elif self.overridden_price is not None:
            return self.overridden_price
        elif self.badge_type == c.ONE_DAY_BADGE:
            return c.get_oneday_price(registered)
        elif self.is_presold_oneday:
            return c.get_presold_oneday_price(self.badge_type)
        if self.badge_type in c.BADGE_TYPE_PRICES:
            return int(c.BADGE_TYPE_PRICES[self.badge_type])
        elif self.age_discount != 0:
            return max(0, c.get_attendee_price(registered) + self.age_discount)
        else:
            return c.get_attendee_price(registered)

    @property
    def amount_unpaid(self):
        if self.paid == c.PAID_BY_GROUP:
            personal_cost = max(0, self.total_cost - c.BADGE_PRICE)
        else:
            personal_cost = self.total_cost
        return max(0, personal_cost - self.amount_paid)
