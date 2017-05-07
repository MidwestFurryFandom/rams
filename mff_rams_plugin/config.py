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
      return [ (1.0, 'Single Table'),(2.0, 'Double Table'),(3.0, 'Triple Table'),(4.0, 'Quad Table'),(5.0, '10x10 Booth')]

    @property
    def ADMIN_TABLE_OPTS(self):
      return [(0.0, 'No Table')] + TABLE_OPTS()
   
    @property
    def PREREG_TABLE_OPTS(self):
      return [(count, '{}: ${}'.format(desc, TABLE_PRICES()[count])) for count, desc in TABLE_OPTS()]
