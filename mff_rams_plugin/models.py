from . import *

@Session.model_mixin
class SessionMixin:
    def all_panelists(self):
        return self.query(Attendee).filter(or_(
            Attendee.ribbon.contains(c.PANELIST_RIBBON),
            Attendee.ribbon == c.STAFF_RIBBON,
            Attendee.badge_type == c.GUEST_BADGE)).order_by(Attendee.full_name).all()

@Session.model_mixin
class Group:
    power = Column(Integer, default=0)
    power_fee = Column(Integer, default=0)
    power_usage = Column(UnicodeText)
    location = Column(UnicodeText, default='', admin_only=True)
    table_fee = Column(Integer, default=0)

    @cost_property
    def power_cost(self):
        return self.power_fee if self.power_fee else c.POWER_PRICES[int(self.power)]

    @cost_property
    def table_cost(self):
        return self.table_fee if self.table_fee else c.TABLE_PRICES[int(self.tables)]

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

    @presave_adjustment
    def never_spam(self):
        self.can_spam = False

    @presave_adjustment
    def not_attending_need_not_pay(self):
        if self.badge_status == c.NOT_ATTENDING:
            self.paid = c.NEED_NOT_PAY
            self.comped_reason = "Automated: Not Attending badge status."

    @presave_adjustment
    def print_ready_before_event(self):
        if c.PRE_CON:
            if self.badge_status == c.COMPLETED_STATUS and not self.is_not_ready_to_checkin\
                    and self.times_printed < 1 and self.ribbon != c.STAFF_RIBBON:
                self.print_pending = True

    @cost_property
    def badge_cost(self):
        registered = self.registered_local if self.registered else None
        if self.paid == c.NEED_NOT_PAY and self.badge_type not in [c.SPONSOR_BADGE, c.SHINY_BADGE]:
            return 0
        elif self.paid == c.NEED_NOT_PAY:
            return c.BADGE_TYPE_PRICES[self.badge_type] - c.get_attendee_price(registered)
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
    def age_discount(self):
        if 'val' in self.age_group_conf and self.age_group_conf['val'] == c.UNDER_13 and c.AT_THE_CON:
            if self.badge_type == c.ATTENDEE_BADGE:
                discount = 30
            elif self.badge_type in [c.FRIDAY, c.SATURDAY, c.SUNDAY]:
                discount = 10
            if not self.age_group_conf['discount'] or self.age_group_conf['discount'] < discount:
                return -discount
        return -self.age_group_conf['discount']

    @property
    def paid_for_a_swag_shirt(self):
        return self.badge_type in [c.SPONSOR_BADGE, c.SHINY_BADGE]
