from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import Form, BooleanField, StringField, PasswordField, IntegerField, TextAreaField, RadioField, \
    SelectField, validators, HiddenField, FileField, DateTimeField
from wtforms_components import TimeField
from flask import g, Flask, current_app
import datetime

from database import get_volunteers_to_select, get_workshops_to_select, get_individual_time_slots_to_select, get_workshop_rooms, get_equipment_groups, get_all_equipment, get_all_badges, get_badge, get_workshop_from_workshop_id


class CreateWorkshopForm(Form):
    workshop_title = StringField("Workshop title", [validators.DataRequired()])
    workshop_description = TextAreaField("Workshop description", [validators.DataRequired()])
    workshop_limit = IntegerField("Workshop max attendees", [validators.InputRequired()])
    workshop_level = RadioField("Workshop level", choices=[("Beginner", "Beginner"), ("Intermediate", "Intermediate"), ("Advanced", "Advanced"), ("Not taught", "Not taught")])
    workshop_url = StringField("Workshop URL (optional)", [validators.Optional(), validators.URL()])
    workshop_volunteer_requirements = IntegerField("Additional Volunteers needed per 10 attendees (optional)")
    workshop_id = HiddenField("Workshop ID", default="")


class AddWorkshopToJam(Form):
    workshop = SelectField("Workshop", choices=get_workshops_to_select())
    volunteer = SelectField("Coordinator", choices=get_volunteers_to_select())
    slot = SelectField("Time slot", choices=get_individual_time_slots_to_select())
    room = SelectField("Room", choices=get_workshop_rooms())
    pilot = SelectField("Pilot", choices=[("False", "False"), ("True", "True")])
    pair = SelectField("Pairs required", choices=[("False", "False"), ("True", "True")])

    def __init__(self, *args, **kwargs):
        super(AddWorkshopToJam, self).__init__(*args, **kwargs)
        self.workshop.choices = [(workshop.workshop_id, workshop.workshop_title) for workshop in get_workshops_to_select()]
        self.volunteer.choices = [(-1, "None")] + get_volunteers_to_select()
        self.room.choices = get_workshop_rooms()


class GetOrderIDForm(Form):
    order_id = IntegerField("Order ID", [validators.DataRequired()])
    day_password = StringField("Jam password", [validators.DataRequired()])


class LoginForm(Form):
    username = StringField("Username", [validators.DataRequired()])
    password = PasswordField("Password", [validators.DataRequired()])


class RegisterUserForm(Form):
    username = StringField("Username", [validators.DataRequired()])
    password = PasswordField("Password", [validators.DataRequired()])
    first_name = StringField("First name", [validators.DataRequired()])
    surname = StringField("Surname", [validators.DataRequired()])
    access_code = StringField("Access code", [validators.DataRequired()])
    email = StringField("Email address - Note must be same used for Slack", [validators.DataRequired()])

    # Added ready to add to Login form itself on page.


class VolunteerAttendance(Form):
    attending_jam = SelectField("Attending Main Jam", choices=[("False", "False"), ("True", "True")])
    attending_setup = SelectField("Attending Setup", choices=[("False", "False"), ("True", "True")])
    attending_packdown = SelectField("Attending Packdown", choices=[("False", "False"), ("True", "True")])
    attending_food = SelectField("Attending Food After", choices=[("False", "False"), ("True", "True")])
    notes = TextAreaField("Notes")
    arrival_time = TimeField("Expected arrival time for Jam", default=datetime.time(hour=11, minute=0))


class ResetPasswordForm(Form):
    username = StringField("Username", [validators.DataRequired()])
    reset_code = StringField("Reset Code", [validators.DataRequired()])
    new_password = PasswordField("New Password", [validators.DataRequired()])


class UploadFileForm(FlaskForm):
    class Meta:
        csrf = False
    file_title = StringField("File title (optional)",)
    file_permission = SelectField("Visibility level", choices=[("Public", "Public"), ("Jam team only", "Jam team only")])
    upload = FileField('File', validators=[
        FileRequired(),
        FileAllowed(("pdf", "ppt", "pptx", "py"), 'Should be a PDF or Powerpoint file!')
    ])


class InventoryForm(Form):
    inventory_title = StringField("Inventory title", [validators.DataRequired()])


class AddEquipmentForm(Form):
    equipment_title = StringField("Equipment title", [validators.DataRequired()])
    equipment_code = StringField("Equipment code", [validators.DataRequired(), validators.Length(3, 3)])
    equipment_group = SelectField("Equipment group", choices=[(str(group.equipment_group_id), group.equipment_group_name) for group in get_equipment_groups()])

    def __init__(self, *args, **kwargs):
        super(AddEquipmentForm, self).__init__(*args, **kwargs)
        self.equipment_group.choices = [(str(group.equipment_group_id), group.equipment_group_name) for group in get_equipment_groups()]


class RoomForm(Form):
    room_id = HiddenField("Workshop room", default="")
    room_name = StringField("Room name", [validators.DataRequired()])
    room_capacity = IntegerField("Room capacity", [validators.DataRequired()])
    room_volunteers_needed = IntegerField("Room volunteers", [validators.DataRequired()])


class SlotForm(Form):
    slot_id = HiddenField("Workshop ID", default="")
    slot_time_start = TimeField("Slot time start", [validators.DataRequired()])
    slot_time_end = TimeField("Slot time finish", [validators.DataRequired()])
    
    
class EquipmentAddToWorkshopForm(FlaskForm):
    equipment_name = SelectField("Equipment name")
    equipment_quantity_needed = IntegerField("Equipment quantity", [validators.DataRequired()])
    per_attendee = RadioField("Allocation", choices=[("True", "Per attendee"), ("False", "Shared equipment")])
    
    def __init__(self, *args, **kwargs):
        super(EquipmentAddToWorkshopForm, self).__init__(*args, **kwargs)
        self.equipment_name.choices = [(str(equipment.equipment_id), equipment.equipment_name) for equipment in get_all_equipment()]


class AddBadgeForm(FlaskForm):
    badge_id = HiddenField("Badge ID")
    badge_name = StringField("Badge name")
    badge_description = StringField("Badge description")


class AddBadgeDependencyForm(FlaskForm):
    badge_id = SelectField("Badge name", coerce=int)
    badge_awarded_core = SelectField("Core badge", choices=[("False", "False"), ("True", "True")])
    
    def __init__(self, *args, **kwargs):
        super(AddBadgeDependencyForm, self).__init__(*args, **kwargs)
        badge_choices = []
        parent_badge = get_badge(kwargs["badge_id"])
        for badge in get_all_badges(include_hidden=True):
            if badge.badge_id != int(parent_badge.badge_id) and not any(b.dependency_badge_id == badge.badge_id for b in parent_badge.dependent_badges):
                badge_choices.append([badge.badge_id, badge.badge_name])
        self.badge_id.choices = badge_choices


class AddBadgeWorkshopForm(FlaskForm):
    badge_id = SelectField("Badge name", coerce=int)
    
    def __init__(self, *args, **kwargs):
        super(AddBadgeWorkshopForm, self).__init__(*args, **kwargs)
        badge_choices = []
        workshop = get_workshop_from_workshop_id(kwargs["workshop_id"])
        for badge in get_all_badges(include_hidden=True):
            if not any(b.badge_id == badge.badge_id for b in workshop.badges):
                badge_choices.append([badge.badge_id, badge.badge_name])
        self.badge_id.choices = badge_choices