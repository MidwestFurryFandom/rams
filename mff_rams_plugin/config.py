from uber.common import *

config = parse_config(__file__)
c.include_plugin_config(config)

@Config.mixin
class ExtraConfig:
    @property
    def DEALER_BADGE_PRICE(self):
        return self.get_attendee_price()

    @property
    def TABLE_OPTS(self):
      return [ (1, 'Single Table'), (2, 'Double Table'), (3, 'Triple Table'), (4, 'Quad Table'), (5, '10x10 Booth') ]

    @property
    def ADMIN_TABLE_OPTS(self):
      return [(0, 'No Table')] + c.TABLE_OPTS
   
    @property
    def PREREG_TABLE_OPTS(self):
      return [(count, '{}: ${}'.format(desc, c.TABLE_PRICES[count])) for count, desc in c.TABLE_OPTS]

    @property
    def POWER_PRICES(self):
        return defaultdict(lambda: config['power_prices'],
                             {int(k): v for k, v in config['power_prices'].items()})

    @property
    def DEALER_POWER_OPTS(self):
        return [ (0, 'No power'), (1, 'Default power') ]
