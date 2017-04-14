from uber.common import *

config = parse_config(__file__)
c.include_plugin_config(config)

c.DEALER_BADGE_PRICE = c.BADGE_PRICE