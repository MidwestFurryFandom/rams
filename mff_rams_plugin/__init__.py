from os.path import join

from uber.jinja import template_overrides
from uber.utils import mount_site_sections, static_overrides
from .config import config
from . import models  # noqa: F401
from . import model_checks  # noqa: F401
from . import automated_emails  # noqa: F401


static_overrides(join(config['module_root'], 'static'))
template_overrides(join(config['module_root'], 'templates'))
mount_site_sections(config['module_root'])
