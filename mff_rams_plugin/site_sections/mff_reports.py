from pockets.autolog import log
from sqlalchemy import func
from sqlalchemy.sql.expression import literal

from uber.config import c
from uber.decorators import all_renderable, csv_file
from uber.models import Attendee, Group


class RegistrationDataOneYear:
    def __init__(self):
        self.event_name = ""

        # what is the final day of this event (i.e. Sunday of a Fri->Sun festival)
        self.end_date = ""

        # this holds how many registrations were taken each day starting at 365 days from the end date of the event.
        # this array is in chronological order and does not skip days.
        #
        # examples:
        # registrations_per_day[0]   is the #regs that were taken on end_date-365 (1 year before the event)
        # .....
        # registrations_per_day[362] is the #regs that were taken on end_date-2 (2 days before the end date)
        # registrations_per_day[363] is the #regs that were taken on end_date-1 (the day before the end date)
        # registrations_per_day[364] is the #regs that were taken on end_date
        self.registrations_per_day = []

        # same as above, but, contains a cumulative sum of the same data
        self.registrations_per_day_cumulative_sum = []

        self.num_days_to_report = 365

    def query_current_year(self, session):
        self.event_name = c.EVENT_NAME_AND_YEAR

        # TODO: we're hacking the timezone info out of ESCHATON (final day of event). probably not the right thing to do
        self.end_date = c.DATES['ESCHATON'].replace(hour=0, minute=0,
                                                    second=0,
                                                    microsecond=0,
                                                    tzinfo=None)

        # return registrations where people actually paid money
        # exclude: dealers
        reg_per_day = session.query(
            func.date_trunc(literal('day'), Attendee.registered),
            func.count(
                func.date_trunc(literal('day'), Attendee.registered))
        ) \
            .outerjoin(Attendee.group) \
            .filter(
            (
                (Attendee.paid == c.PAID_BY_GROUP) &  # if they're paid by group
                (Group.amount_paid >= Group.cost)  # make sure they've paid something, or are comped
            ) | (  # OR
                (Attendee.badge_status == c.COMPLETED_STATUS)
                # if they're an attendee, make sure they're check-in-able
            )
        ) \
            .group_by(func.date_trunc(literal('day'), Attendee.registered)) \
            .order_by(func.date_trunc(literal('day'), Attendee.registered)) \
            .all()  # noqa: E711

        # now, convert the query's data into the format we need.
        # SQL will skip days without registrations
        # we need all self.num_days_to_report days to have data, even if it's zero

        # create 365 elements in the final array
        self.registrations_per_day = self.num_days_to_report * [0]

        for reg_data in reg_per_day:
            day = reg_data[0]
            reg_count = reg_data[1]

            day_offset = self.num_days_to_report - (
                self.end_date - day).days
            day_index = day_offset - 1

            if day_index < 0 or day_index >= self.num_days_to_report:
                log.info(
                    "Ignoring some analytics data because it's not in range of the year before c.ESCHATON. "
                    "Either c.ESCHATON is set incorrectly or you have registrations starting 1 year before ESCHATON, "
                    "or occuring after ESCHATON. day_index=" + str(
                        day_index))
                continue

            self.registrations_per_day[day_index] = reg_count

        self.compute_cumulative_sum_from_registrations_per_day()

    # compute cumulative sum up until the last non-zero data point
    def compute_cumulative_sum_from_registrations_per_day(self):

        if len(self.registrations_per_day) != self.num_days_to_report:
            raise 'array validation error: array size should be the same as the report size'

        # figure out where the last non-zero data point is in the array
        last_useful_data_index = self.num_days_to_report - 1
        for regs in reversed(self.registrations_per_day):
            if regs != 0:
                break  # found it, so we're done.
            last_useful_data_index -= 1

        # compute the cumulative sum, leaving all numbers past the last data point at zero
        self.registrations_per_day_cumulative_sum = self.num_days_to_report * [
            0]
        total_so_far = 0
        current_index = 0
        for regs_this_day in self.registrations_per_day:
            total_so_far += regs_this_day
            self.registrations_per_day_cumulative_sum[
                current_index] = total_so_far
            if current_index == last_useful_data_index:
                break
            current_index += 1

    def dump_data(self):
        return {
            "registrations_per_day": self.registrations_per_day,
            "registrations_per_day_cumulative_sum": self.registrations_per_day_cumulative_sum,
            "event_name": self.event_name,
            "event_end_date": self.end_date.strftime("%d-%m-%Y"),
        }

@all_renderable(c.PEOPLE, c.STATS)
class Root:
    def index(self, session):
        pass

    def comped_badges(self, session, message='', show='all'):
        all_comped = session.valid_attendees()\
            .filter(Attendee.paid == c.NEED_NOT_PAY)
        claimed_comped = all_comped.filter(Attendee.placeholder == False)
        unclaimed_comped = all_comped.filter(Attendee.placeholder == True)
        if show == 'claimed':
            comped_attendees = claimed_comped
        elif show == 'unclaimed':
            comped_attendees = unclaimed_comped
        else:
            comped_attendees = all_comped

        return {
            'message': message,
            'comped_attendees': comped_attendees,
            'all_comped': all_comped.count(),
            'claimed_comped': claimed_comped.count(),
            'unclaimed_comped': unclaimed_comped.count(),
            'show': show
        }

    def attendance_graph(self, session):
        graph_data_current_year = RegistrationDataOneYear()
        graph_data_current_year.query_current_year(session)

        return {
            'current_registrations': graph_data_current_year.dump_data(),
        }

    @csv_file
    def all_dealers_detailed(self, out, session ):
        out.writerow([
            'Business Name',
            'Dealer Name',
            'Status',
            'Description',
            'URL',
            'Point of Contact',
            'Email',
            'Phone Number',
            'Address1',
            'Address2',
            'City',
            'State/Region',
            'Zip Code',
            'Country',
            'Tables',
            'Amount Paid',
            'Cost',
            'Badges',
            'Wares',
            'Wares - Other'
        ])
        dealer_groups = session.query(Group).filter(Group.tables > 0).all()
        for group in dealer_groups:
            if group.is_dealer:
                full_name = group.leader.full_name if group.leader else ''
                out.writerow([
                    group.name,
                    full_name,
                    group.status_label,
                    group.description,
                    group.website,
                    group.leader.legal_name or group.leader.full_name,
                    group.leader.email,
                    group.leader.cellphone,
                    group.address1,
                    group.address2,
                    group.city,
                    group.region,
                    group.zip_code,
                    group.country,
                    group.tables,
                    group.amount_paid,
                    group.cost,
                    group.badges,
                    group.categories_labels,
                    group.categories_text
                ])
    @csv_file
    def dealers_publication_listing(self, out, session ):
        out.writerow([
            'Business Name',
            'Description',
            'URL',
            'Location'
        ])
        dealer_groups = session.query(Group).filter(Group.tables > 0).all()
        for group in dealer_groups:
            if group.is_dealer and group.status_label == 'Approved':
                out.writerow([
                    group.name,
                    group.description,
                    group.website,
                    group.location
                ])
