from sideboard.lib import parse_config
from collections import defaultdict

from uber.config import c, Config
from uber.menu import MenuItem

config = parse_config(__file__)
c.include_plugin_config(config)

c.MENU.append_menu_item(
    MenuItem(name='Midwest FurFest', access=c.PEOPLE, submenu=[
        MenuItem(name='Comped Badges', href='../mff_reports/comped_badges'),
        MenuItem(name='Daily Attendance', href='../mff_reports/attendance_graph'),
        MenuItem(name='Print Adult Badges',
                 href='../kiosk_printing/print_badges'),
        MenuItem(name='Print Minor Badges',
                 href='../kiosk_printing/print_badges?minor=True'),
    ])
)


@Config.mixin
class ExtraConfig:
    @property
    def DEALER_BADGE_PRICE(self):
        return self.get_attendee_price()

    @property
    def TABLE_OPTS(self):
        return [(1, 'Single Table'),
                (2, 'Double Table'),
                (3, 'Triple Table'),
                (4, 'Quad Table'),
                (5, '10x10 Booth')]

    @property
    def ADMIN_TABLE_OPTS(self):
        return [(0, 'No Table')] + c.TABLE_OPTS

    @property
    def PREREG_TABLE_OPTS(self):
        return [(count, '{}: ${}'.format(desc, c.TABLE_PRICES[count]))
              for count, desc in c.TABLE_OPTS]

    @property
    def POWER_PRICES(self):
        return defaultdict(
            lambda: config['power_prices'],
            {int(k): v for k, v in config['power_prices'].items()})

    @property
    def DEALER_POWER_OPTS(self):
        return [(0, 'No power'), (1, 'Default power')]
