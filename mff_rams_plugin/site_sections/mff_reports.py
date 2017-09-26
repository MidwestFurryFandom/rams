from uber.common import *


@all_renderable(c.PEOPLE)
class Root:
    def index(self, session):
        pass

    def comped_badges(self, session, message='', show='all'):
        all_comped = session.valid_attendees().filter(Attendee.paid == c.NEED_NOT_PAY)
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