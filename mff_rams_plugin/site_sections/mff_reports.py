from uber.config import c
from uber.decorators import all_renderable, csv_file
from uber.models import Attendee, Group

@all_renderable(c.PEOPLE)
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
