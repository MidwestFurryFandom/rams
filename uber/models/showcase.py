import os
import re
import cherrypy

from datetime import datetime, timedelta
from functools import wraps
from pockets import sluggify
from pockets.autolog import log
from pytz import UTC
from residue import CoerceUTF8 as UnicodeText, UTCDateTime, UUID
from sqlalchemy import func
from sqlalchemy.schema import ForeignKey, UniqueConstraint
from sqlalchemy.types import Boolean, Integer
from sqlalchemy.ext.hybrid import hybrid_property

from uber.config import c
from uber.decorators import presave_adjustment
from uber.models import MagModel, Attendee
from uber.models.types import default_relationship as relationship, utcnow, \
    Choice, DefaultColumn as Column, MultiChoice, GuidebookImageMixin, UniqueList
from uber.utils import localized_now, make_url


__all__ = [
    'IndieJudge', 'IndieStudio', 'IndieDeveloper', 'IndieGame',
    'IndieGameImage', 'IndieGameCode', 'IndieGameReview']


class ReviewMixin:
    @property
    def game_reviews(self):
        return [r for r in self.reviews if r.game_status != c.PENDING]


class IndieJudge(MagModel, ReviewMixin):
    admin_id = Column(UUID, ForeignKey('admin_account.id'))
    status = Column(Choice(c.MIVS_JUDGE_STATUS_OPTS), default=c.UNCONFIRMED)
    no_game_submission = Column(Boolean, nullable=True)
    genres = Column(MultiChoice(c.MIVS_INDIE_JUDGE_GENRE_OPTS))
    platforms = Column(MultiChoice(c.MIVS_INDIE_PLATFORM_OPTS))
    platforms_text = Column(UnicodeText)
    vr_text = Column(UnicodeText)
    staff_notes = Column(UnicodeText)

    codes = relationship('IndieGameCode', backref='judge')
    reviews = relationship('IndieGameReview', backref='judge')

    email_model_name = 'judge'

    @property
    def judging_complete(self):
        return len(self.reviews) == len(self.game_reviews)

    @property
    def mivs_all_genres(self):
        return c.MIVS_ALL_GENRES in self.genres_ints

    @property
    def attendee(self):
        return self.admin_account.attendee

    @property
    def full_name(self):
        return self.attendee.full_name

    @property
    def email(self):
        return self.attendee.email

    def get_code_for(self, game_id):
        codes_for_game = [code for code in self.codes if code.game_id == game_id]
        return codes_for_game[0] if codes_for_game else ''


class IndieStudio(MagModel):
    group_id = Column(UUID, ForeignKey('group.id'), nullable=True)
    name = Column(UnicodeText, unique=True)
    website = Column(UnicodeText)
    other_links = Column(UniqueList)

    status = Column(
        Choice(c.MIVS_STUDIO_STATUS_OPTS), default=c.NEW, admin_only=True)
    staff_notes = Column(UnicodeText, admin_only=True)
    registered = Column(UTCDateTime, server_default=utcnow(), default=lambda: datetime.now(UTC))

    accepted_core_hours = Column(Boolean, default=False)
    discussion_emails = Column(UnicodeText)
    completed_discussion = Column(Boolean, default=False)
    read_handbook = Column(Boolean, default=False)
    training_password = Column(UnicodeText)
    selling_at_event = Column(Boolean, nullable=True, admin_only=True)  # "Admin only" preserves null default
    needs_hotel_space = Column(Boolean, nullable=True, admin_only=True)  # "Admin only" preserves null default
    name_for_hotel = Column(UnicodeText)
    email_for_hotel = Column(UnicodeText)
    contact_phone = Column(UnicodeText)
    show_info_updated = Column(Boolean, default=False)

    games = relationship(
        'IndieGame', backref='studio', order_by='IndieGame.title')
    developers = relationship(
        'IndieDeveloper',
        backref='studio',
        order_by='IndieDeveloper.last_name')

    email_model_name = 'studio'

    @property
    def primary_contact_first_names(self):
        if not self.primary_contacts:
            return ''

        if len(self.primary_contacts) == 1:
            return self.primary_contacts[0].first_name

        string = self.primary_contacts[0].first_name
        for dev in self.primary_contacts[1:-1]:
            string += ", " + dev.first_name
        if len(self.primary_contacts) > 2:
            string += ","
        string += " and " + self.primary_contacts[-1].first_name
        return string

    @property
    def mivs_games(self):
        return [g for g in self.games if g.showcase_type == c.MIVS]

    @property
    def arcade_games(self):
        return [g for g in self.games if g.showcase_type == c.ARCADE]

    @property
    def confirm_deadline(self):
        sorted_games = sorted(
            [g for g in self.games if g.accepted], key=lambda g: g.accepted)
        confirm_deadline = timedelta(days=c.MIVS_CONFIRM_DEADLINE)
        return sorted_games[0].accepted + confirm_deadline if len(sorted_games) else None

    @property
    def after_confirm_deadline(self):
        return self.confirm_deadline < localized_now()

    @property
    def discussion_emails_list(self):
        return list(filter(None, self.discussion_emails.split(',')))

    @property
    def discussion_emails_last_updated(self):
        studio_updates = self.get_tracking_by_instance(self, action=c.UPDATED, last_only=False)
        for update in studio_updates:
            if 'discussion_emails' in update.data:
                return update.when

    @property
    def core_hours_status(self):
        return "Accepted" if self.accepted_core_hours else None

    @property
    def discussion_status(self):
        return "Completed" if self.completed_discussion else None

    @property
    def handbook_status(self):
        return "Read" if self.read_handbook else None

    @property
    def training_status(self):
        if self.training_password:
            return "Completed" if self.training_password.lower() == c.MIVS_TRAINING_PASSWORD.lower()\
                else "Entered the wrong phrase!"

    @property
    def selling_at_event_status(self):
        if self.selling_at_event is not None:
            return "Expressed interest in selling" if self.selling_at_event else "Opted out"

    @property
    def hotel_space_status(self):
        if self.needs_hotel_space is not None:
            return "Requested hotel space for {} with email {}".format(self.name_for_hotel, self.email_for_hotel)\
                if self.needs_hotel_space else "Opted out"

    @property
    def show_info_status(self):
        return self.show_info_updated

    def checklist_deadline(self, slug):
        default_deadline = c.MIVS_CHECKLIST[slug]['deadline']
        if self.group and self.group.registered >= default_deadline and slug in ['core_hours', 'discussion']:
            return self.group.registered + timedelta(days=7)
        return default_deadline

    def past_checklist_deadline(self, slug):
        """

        Args:
            slug: A standardized name, which should match the checklist's section name in config.
            E.g., the properties above ending in _status

        Returns: A timedelta object representing how far from the deadline this team is for a particular checklist item

        """
        return localized_now() - self.checklist_deadline(slug)

    @property
    def checklist_items_due_soon_grouped(self):
        due_soon = []
        overdue = []
        for key, val in c.MIVS_CHECKLIST.items():
            if not getattr(self, key + "_status", None):
                if localized_now() >= self.checklist_deadline(key):
                    overdue.append((key, val['name']))
                elif (localized_now() + timedelta(days=3)) >= self.checklist_deadline(key):
                    due_soon.append((key, val['name']))

        return due_soon, overdue

    @property
    def website_href(self):
        return make_url(self.website)

    @property
    def email(self):
        return [dev.email_to_address for dev in self.developers if dev.gets_emails]

    @property
    def primary_contacts(self):
        return [dev for dev in self.developers if dev.gets_emails]

    @property
    def submitted_games(self):
        return [g for g in self.games if g.submitted]

    @property
    def confirmed_games(self):
        return [g for g in self.games if g.confirmed]

    @property
    def comped_badges(self):
        game_count = len([g for g in self.games if g.status == c.ACCEPTED])
        return c.MIVS_INDIE_BADGE_COMPS * game_count

    @property
    def unclaimed_badges(self):
        claimed_count = len(
            [d for d in self.developers if not d.attendee])
        return max(0, self.comped_badges - claimed_count)


class IndieDeveloper(MagModel):
    studio_id = Column(UUID, ForeignKey('indie_studio.id'))
    attendee_id = Column(UUID, ForeignKey('attendee.id'), nullable=True)

    gets_emails = Column(Boolean, default=False)
    first_name = Column(UnicodeText)
    last_name = Column(UnicodeText)
    email = Column(UnicodeText)
    cellphone = Column(UnicodeText)
    agreed_coc = Column(Boolean, default=False)
    agreed_data_policy = Column(Boolean, default=False)

    @property
    def email_to_address(self):
        return self.attendee.email if self.attendee else self.email

    @property
    def cellphone_num(self):
        return self.attendee.cellphone if self.attendee else self.cellphone

    @property
    def full_name(self):
        return self.first_name + ' ' + self.last_name

    @property
    def matching_attendee(self):
        return self.session.query(Attendee).filter(
            func.lower(Attendee.first_name) == self.first_name.lower(),
            func.lower(Attendee.last_name) == self.last_name.lower(),
            func.lower(Attendee.email) == self.email.lower()
        ).first()


class IndieGame(MagModel, ReviewMixin):
    studio_id = Column(UUID, ForeignKey('indie_studio.id'))
    title = Column(UnicodeText)
    brief_description = Column(UnicodeText)
    genres = Column(MultiChoice(c.MIVS_INDIE_GENRE_OPTS))
    genres_text = Column(UnicodeText)
    has_multiplayer = Column(Boolean, default=False)
    player_count = Column(UnicodeText)
    platforms = Column(MultiChoice(c.MIVS_INDIE_PLATFORM_OPTS))
    platforms_text = Column(UnicodeText)
    requires_gamepad = Column(Boolean, default=False)
    is_alumni = Column(Boolean, default=False)
    content_warning = Column(Boolean, default=False)
    warning_desc = Column(UnicodeText)
    photosensitive_warning = Column(Boolean, default=False)
    description = Column(UnicodeText)

    how_to_play = Column(UnicodeText)
    link_to_video = Column(UnicodeText)
    link_to_game = Column(UnicodeText)
    password_to_game = Column(UnicodeText)
    code_type = Column(Choice(c.MIVS_CODE_TYPE_OPTS), default=c.NO_CODE)
    code_instructions = Column(UnicodeText)
    build_status = Column(
        Choice(c.MIVS_BUILD_STATUS_OPTS), default=c.PRE_ALPHA)
    build_notes = Column(UnicodeText)

    agreed_liability = Column(Boolean, default=False)
    agreed_showtimes = Column(Boolean, default=False)

    link_to_promo_video = Column(UnicodeText)
    link_to_webpage = Column(UnicodeText)
    twitter = Column(UnicodeText)
    facebook = Column(UnicodeText)
    other_social_media = Column(UnicodeText)

    tournament_at_event = Column(Boolean, default=False)
    tournament_prizes = Column(UnicodeText)
    multiplayer_game_length = Column(Integer, nullable=True) # Length in minutes
    leaderboard_challenge = Column(Boolean, default=False)

    showcase_type = Column(Choice(c.SHOWCASE_GAME_TYPE_OPTS), default=c.MIVS)
    submitted = Column(Boolean, default=False)
    status = Column(
        Choice(c.MIVS_GAME_STATUS_OPTS), default=c.NEW, admin_only=True)
    judge_notes = Column(UnicodeText, admin_only=True)
    registered = Column(UTCDateTime, server_default=utcnow(), default=lambda: datetime.now(UTC))
    waitlisted = Column(UTCDateTime, nullable=True)
    accepted = Column(UTCDateTime, nullable=True)

    codes = relationship('IndieGameCode', backref='game')
    reviews = relationship('IndieGameReview', backref='game')
    images = relationship(
        'IndieGameImage', backref='game', order_by='IndieGameImage.id')

    email_model_name = 'game'

    @presave_adjustment
    def accepted_time(self):
        if self.status == c.ACCEPTED and not self.accepted:
            self.accepted = datetime.now(UTC)

    @presave_adjustment
    def waitlisted_time(self):
        if self.status == c.WAITLISTED and not self.waitlisted:
            self.waitlisted = datetime.now(UTC)

    @property
    def email(self):
        return self.studio.email

    @property
    def reviews_to_email(self):
        return [review for review in self.reviews if review.send_to_studio]

    @property
    def video_href(self):
        return make_url(self.link_to_video)

    @property
    def href(self):
        return make_url(self.link_to_game)

    @property
    def screenshots(self):
        return [img for img in self.images if img.is_screenshot]

    @property
    def best_screenshots(self):
        return [
            img for img in self.images
            if img.is_screenshot and img.use_in_promo]

    def accepted_image_downloads(self, count=2):
        all_screenshots = reversed(sorted(
            [image for image in self.images if not image.is_header and not image.is_thumbnail],
            key=lambda img: (
                img.is_screenshot and img.use_in_promo,
                img.is_screenshot,
                img.use_in_promo)))

        screenshots = []
        for i, screenshot in enumerate(all_screenshots):
            if os.path.exists(screenshot.filepath):
                screenshots.append(screenshot)
                if len(screenshots) >= count:
                    break
        if self.guidebook_header:
            screenshots.append(self.guidebook_header)
        if self.guidebook_thumbnail:
            screenshots.append(self.guidebook_thumbnail)
        return screenshots

    def accepted_image_download_filenames(self, count=2):
        nonchars = re.compile(r'[\W]+')
        accepted_images = self.accepted_image_downloads(count)
        screenshots = []
        for i, screenshot in enumerate(accepted_images):
            if os.path.exists(screenshot.filepath):
                name = '_'.join([s for s in self.title.lower().split() if s])
                name = nonchars.sub('', name)
                if screenshot.is_header:
                    filename = f'{name}_header.{screenshot.extension.lower()}'
                elif screenshot.is_thumbnail:
                    filename = f'{name}_icon.{screenshot.extension.lower()}'
                else:
                    filename = '{}_{}.{}'.format(
                        name, len(screenshots) + 1, screenshot.extension.lower())
                screenshots.append(filename)
                if len(screenshots) >= (count + 2):
                    break
        return screenshots + ([''] * ((count + 2) - len(screenshots)))

    @property
    def promo_image(self):
        return next(
            iter([img for img in self.images if not img.is_screenshot]), None)

    @property
    def missing_steps(self):
        steps = []
        if self.code_type != c.NO_CODE and self.link_to_game:
            if not self.codes:
                steps.append(
                    f'attach one unlimited-use code or {c.MIVS_CODES_REQUIRED} individual codes for our judges')
            elif not self.unlimited_code \
                    and len(self.codes) < c.MIVS_CODES_REQUIRED:
                steps.append(
                    f'attach at least {c.MIVS_CODES_REQUIRED} codes for our judges')
        if len(self.screenshots) < 2:
            steps.append('upload at least two screenshots')

        return steps

    @property
    def video_broken(self):
        for r in self.reviews:
            if r.video_status == c.BAD_LINK:
                return True

    @property
    def unlimited_code(self):
        for code in self.codes:
            if code.unlimited_use:
                return code

    @property
    def scores(self):
        return [r.game_score for r in self.reviews if r.game_score]

    @property
    def score_sum(self):
        return sum(self.scores, 0)

    @property
    def average_score(self):
        return (self.score_sum / len(self.scores)) if self.scores else 0

    @property
    def has_issues(self):
        return any(r.has_issues for r in self.reviews)

    @property
    def confirmed(self):
        return self.status == c.ACCEPTED \
            and self.studio \
            and self.studio.group_id

    @hybrid_property
    def has_been_accepted(self):
        return self.status == c.ACCEPTED

    @property
    def guidebook_header(self):
        for image in self.images:
            if image.is_header:
                return image
        return ''

    @property
    def guidebook_thumbnail(self):
        for image in self.images:
            if image.is_thumbnail:
                return image
        return ''

    @property
    def guidebook_edit_link(self):
        return f"../mivs/show_info?id={self.id}"

    @property
    def guidebook_data(self):
        return {
            'guidebook_name': self.title,
            'guidebook_subtitle': self.studio.name,
            'guidebook_desc': self.description,
            'guidebook_location': '',
            'guidebook_header': self.guidebook_images[0][0],
            'guidebook_thumbnail': self.guidebook_images[0][1],
        }

    @property
    def guidebook_images(self):
        if not self.images:
            return ['', ''], ['', '']

        header = self.guidebook_header
        thumbnail = self.guidebook_thumbnail
        prepend = sluggify(self.title) + '_'

        header_name = (prepend + header.filename) if header else ''
        thumbnail_name = (prepend + thumbnail.filename) if thumbnail else ''
        
        return [header_name, thumbnail_name], [header, thumbnail]


class IndieGameImage(MagModel, GuidebookImageMixin):
    game_id = Column(UUID, ForeignKey('indie_game.id'))
    description = Column(UnicodeText)
    use_in_promo = Column(Boolean, default=False)
    is_screenshot = Column(Boolean, default=True)

    @property
    def image(self):
        from markupsafe import Markup

        if not self.filename:
            return ''
        return Markup(
            f"""<a href="{self.url}" target="_blank">{self.filename}</a>""")

    @image.setter
    def image(self, value):
        import shutil
        import cherrypy

        if not isinstance(value, cherrypy._cpreqbody.Part):
            log.error(f"Tried to set image for game {self.game.title} with invalid value type: {type(value)}")
            return

        self.filename = value.filename
        self.content_type = value.content_type.value
        self.extension = value.filename.split('.')[-1].lower()

        with open(self.filepath, 'wb') as f:
            shutil.copyfileobj(value.file, f)

    @property
    def url(self):
        return f"../mivs/view_image?id={self.id}"

    @property
    def filepath(self):
        return os.path.join(c.MIVS_GAME_IMAGE_DIR, str(self.id))


class IndieGameCode(MagModel):
    game_id = Column(UUID, ForeignKey('indie_game.id'))
    judge_id = Column(UUID, ForeignKey('indie_judge.id'), nullable=True)
    code = Column(UnicodeText)
    unlimited_use = Column(Boolean, default=False)
    judge_notes = Column(UnicodeText, admin_only=True)

    @property
    def type_label(self):
        return 'Unlimited-Use' if self.unlimited_use else 'Single-Person'


class IndieGameReview(MagModel):
    game_id = Column(UUID, ForeignKey('indie_game.id'))
    judge_id = Column(UUID, ForeignKey('indie_judge.id'))
    video_status = Column(
        Choice(c.MIVS_VIDEO_REVIEW_STATUS_OPTS), default=c.PENDING)
    game_status = Column(
        Choice(c.MIVS_GAME_REVIEW_STATUS_OPTS), default=c.PENDING)
    game_content_bad = Column(Boolean, default=False)
    read_how_to_play = Column(Boolean, default=False)

    # 0 = not reviewed, 1-10 score (10 is best)
    readiness_score = Column(Integer, default=0)
    design_score = Column(Integer, default=0)
    enjoyment_score = Column(Integer, default=0)
    game_review = Column(UnicodeText)
    developer_response = Column(UnicodeText)
    staff_notes = Column(UnicodeText)
    send_to_studio = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('game_id', 'judge_id', name='review_game_judge_uniq'),
    )

    @property
    def game_score(self):
        if self.has_game_issues or not (self.readiness_score and self.design_score and self.enjoyment_score):
            return 0
        return sum([self.readiness_score, self.design_score, self.enjoyment_score]) / float(3)

    @property
    def has_video_issues(self):
        return self.video_status in c.MIVS_PROBLEM_STATUSES

    @property
    def has_game_issues(self):
        if self.game_status != c.COULD_NOT_PLAY:
            return self.game_status in c.MIVS_PROBLEM_STATUSES

    @property
    def has_issues(self):
        return self.has_video_issues or self.has_game_issues

