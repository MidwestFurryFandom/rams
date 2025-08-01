import cherrypy

from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from pockets.autolog import log

from uber.config import c
from uber.decorators import all_renderable, ajax
from uber.errors import HTTPRedirect
from uber.forms import load_forms
from uber.models import PanelApplicant, PanelApplication
from uber.utils import add_opt, check, localized_now, validate_model


def get_other_panelists_forms(num, submitter=None, **params):
    panelist_form_list = ['PanelistInfo', 'PanelistCredentials']

    if submitter:
        panelist_forms = {0: load_forms(params, submitter, panelist_form_list)}
    else:
        panelist_forms = {}

    for i in range(1, int(num) + 1):
        panelist_forms[i] = load_forms(params, PanelApplicant(), panelist_form_list, field_prefix=str(i))
    return panelist_forms


@all_renderable(public=True)
class Root:
    def index(self, session, message='', attendee_id=None, return_to='', **params):
        """
        Our production NGINX config caches the page at /panels/index.
        Since it's cached, we CAN'T return a session cookie with the page. We
        must POST to a different URL in order to bypass the cache and get a
        valid session cookie. Thus, this page is also exposed as "post_index".
        """
        app = PanelApplication(length=0, record=0)
        is_guest = False
        readonly_fields = {}

        if attendee_id:
            attendee = session.attendee(id=attendee_id)
            if attendee.badge_type != c.GUEST_BADGE:
                add_opt(attendee.ribbon_ints, c.PANELIST_RIBBON)
            is_guest = attendee.group if attendee.group.guest else None
            if attendee.panel_applicants:
                panelist = sorted(attendee.panel_applicants, key=lambda p: p.submitter)[0]
                for attr in ['first_name', 'last_name', 'email', 'cellphone']:
                    setattr(panelist, attr, getattr(attendee, attr))
            else:
                panelist = PanelApplicant(
                    attendee_id=attendee.id,
                    first_name=attendee.first_name,
                    last_name=attendee.last_name,
                    email=attendee.email,
                    cellphone=attendee.cellphone
                )
        else:
            panelist = PanelApplicant()
            for attr in ['first_name', 'last_name', 'email', 'cellphone']:
                if params.get(attr, None):
                    setattr(panelist, attr, params[attr])
                    readonly_fields[attr] = True

        panelist_forms = get_other_panelists_forms(4, submitter=panelist, **params)
        form_list = ['PanelInfo', 'PanelOtherInfo']
        if not is_guest:
            form_list.append('PanelConsents')
        forms = load_forms(params, app, form_list)
        
        num_other_panelists = int(params.get('other_panelists_select', 0))

        if cherrypy.request.method == 'POST':
            for form in panelist_forms[0].values():
                form.populate_obj(panelist)

            if not attendee_id:
                dupe_panelist = session.query(PanelApplicant).filter(
                    PanelApplicant.submitter == True, PanelApplicant.first_name == panelist.first_name,
                    PanelApplicant.last_name == panelist.last_name, PanelApplicant.email == panelist.email).first()
                if dupe_panelist:
                    dupe_panelist.cellphone = panelist.cellphone
                    panelist = dupe_panelist

            panelist.applications.append(app)
            panelist.submitter = True
            app.submitter_id = panelist.id
            session.add(panelist)

            for form in forms.values():
                form.populate_obj(app)
                session.add(app)
            
            for num in range(1, num_other_panelists + 1):
                other_panelist = PanelApplicant()
                other_panelist.applications.append(app)

                for form in panelist_forms[num].values():
                    form.populate_obj(other_panelist)
                session.add(other_panelist)
            
            message = "Your panel application has been submitted."

            if params.get('additional_panel', None):
                message += " You can fill out another application below."
                if attendee_id:
                    raise HTTPRedirect(f"index?attendee_id={attendee_id}&message={message}&return_to={
                        return_to if 'ignore_return_to' not in params else ''}")
                raise HTTPRedirect("index?first_name={}&last_name={}&email={}&cellphone={}&message={}",
                                   panelist.first_name, panelist.last_name,
                                   panelist.email, panelist.cellphone, message)
                
            go_to = (return_to + "&") if 'ignore_return_to' not in params and return_to else 'index?'
            raise HTTPRedirect(f'{go_to}message={message}')

        return {
            'app': app,
            'forms': forms,
            'panelist_forms': panelist_forms,
            'message': message,
            'panelist': panelist,
            'other_panelists': num_other_panelists,
            'is_guest': is_guest,
            'return_to': return_to,
            'attendee_id': attendee_id,
            'readonly_fields': readonly_fields,
        }

    @ajax
    def validate_panel_app(self, session, form_list=[], **params):
        panelist_form_list = []

        if not form_list:
            form_list = ['PanelInfo', 'PanelOtherInfo']
            if not params.get('is_guest', None):
                form_list.append('PanelConsents')
            panelist_form_list = ['PanelistInfo', 'PanelistCredentials']
        elif isinstance(form_list, str):
            form_list = [form_list]
        
        for form_name in form_list:
            if form_name.startswith('Panelist'):
                panelist_form_list.append(form_name)
                form_list.remove(form_name)

        all_errors = {}

        num_other_panelists = int(params.get('other_panelists_select', 0))
        panelist_forms = get_other_panelists_forms(num_other_panelists, submitter=PanelApplicant(), **params)
        for index, loaded_forms in panelist_forms.items():
            errors = validate_model(loaded_forms, PanelApplicant())
            if errors:
                all_errors.update(errors)

        forms = load_forms(params, PanelApplication(), form_list)
        panel_errors = validate_model(forms, PanelApplication())
        if panel_errors:
            all_errors.update(panel_errors)

        if all_errors:
            return {"error": all_errors}

        return {"success": True}

    def confirm_panel(self, session, id):
        app = session.panel_application(id)
        app.confirmed = datetime.now()
        session.add(app)
        session.commit()

        return {
            'app': app,
        }
