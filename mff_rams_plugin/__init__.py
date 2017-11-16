from uber.common import *
from ._version import __version__
from .config import *
from .models import *
from .model_checks import *
from .automated_emails import *

static_overrides(join(config['module_root'], 'static'))
template_overrides(join(config['module_root'], 'templates'))
mount_site_sections(config['module_root'])


c.MENU.append_menu_item(MenuItem(name='Midwest FurFest', access=c.PEOPLE, submenu=[
    MenuItem(name='Comped Badges', href='../mff_reports/comped_badges'),
    MenuItem(name='Print Adult Badges', href='../kiosk_printing/print_badges'),
    MenuItem(name='Print Minor Badges', href='../kiosk_printing/print_badges?minor=True'),
                                 ])
                        )
