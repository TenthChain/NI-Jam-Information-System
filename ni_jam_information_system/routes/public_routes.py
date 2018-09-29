from flask import Blueprint, render_template, request, make_response, redirect, flash, send_file, abort
import database
from datetime import datetime, timedelta
from secrets.config import *
import forms as forms
import logins
from decorators import *
import configuration


public_routes = Blueprint('public_routes', __name__,
                        template_folder='templates')


@public_routes.route('/', methods=['POST', 'GET'])
def index():
    if not configuration.verify_config_item_bool("modules", "module_core"):
        return "Core module not enabled. Enable it by adding under the [modules] section in {}, module_core = true.".format(configuration.config_file_location)
    cookie = request.cookies.get('jam_order_id')
    if cookie and len(cookie) == 9 and database.verify_attendee_id(cookie, database.get_current_jam_id()):
        return redirect("workshops")
    form = forms.GetOrderIDForm(request.form)
    if request.method == 'POST' and form.validate():
        if database.verify_attendee_id(form.order_id.data, database.get_current_jam_id()) and form.day_password.data == day_password:
            resp = make_response(redirect("workshops"))
            resp.set_cookie('jam_order_id', str(form.order_id.data), expires=(datetime.now() + timedelta(hours=6)))
            resp.set_cookie('jam_id', str(database.get_current_jam_id()))
            return resp
        else:
            flash("Error, no order with that ID found or Jam password is wrong. Please try again.", "danger")
            return render_template('index.html', form=form)
    return render_template('index.html', form=form)


@public_routes.route("/login", methods=['POST', 'GET'])
@module_core_required
def login():
    cookie_value = request.cookies.get("jam_login")
    next = logins.get_redirect_target()
    if cookie_value:
        valid, cookie = logins.validate_cookie(cookie_value)
        if valid:
            return redirect('admin/admin_home')

    form = forms.LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        login_validated, user = logins.validate_login(form.username.data, form.password.data)
        if login_validated:
            resp = make_response(logins.redirect_back('admin_routes.admin_home'))
            resp.set_cookie("jam_login", database.new_cookie_for_user(user.user_id))
            return resp
        if user:
            flash("This user account has been disabled and so can not be logged into.", "danger")
        else:
            flash("Unable to login, credentials incorrect.", "danger")
        return render_template("login.html", form=form)
    return render_template("login.html", next=next, form=form)


@public_routes.route("/register", methods=['POST', 'GET'])
@module_core_required
def register():
    form = forms.RegisterUserForm(request.form)
    if request.method == 'POST' and form.validate():
        if form.access_code.data == access_code and not database.get_user_details_from_username(form.username.data):
            salt, bcrypt_password = logins.create_password_salt(form.password.data)
            database.create_user(form.username.data, bcrypt_password, salt, form.first_name.data, form.surname.data, form.email.data)
            return 'New user account created! <meta http-equiv="refresh" content="3;url=/login" />'
        return "Error, unable to create user account. User may already exist or access code may be incorrect"
    return(render_template("register.html", form=form))


@public_routes.route("/reset", methods=['GET', 'POST'])
@module_core_required
def reset_password():
    form = forms.ResetPasswordForm(request.form)
    if request.method == 'POST' and form.validate():
        salt, hash = logins.create_password_salt(form.new_password.data)
        if database.reset_password(form.username.data, form.reset_code.data, salt, hash):
            return redirect("/login")
        return render_template("reset_password.html", form=form, error="Reset failed, credentials provided are invalid.")
    return render_template("reset_password.html", form=form)


@public_routes.route("/logout")
@module_core_required
def logout():
    resp = make_response(redirect("/"))
    login_cookie = request.cookies.get("jam_login")
    if login_cookie:
        database.remove_cookie(login_cookie)
    resp.set_cookie('jam_order_id', "", expires=0)
    resp.set_cookie('jam_login', "", expires=0)
    resp.set_cookie('jam_month', "", expires=0)
    return resp


@public_routes.route("/public_schedule")
@module_public_schedule_required
def public_schedule():
    time_slots, workshop_rooms_in_use =database.get_workshop_timetable_data(database.get_current_jam_id())
    return render_template("public_schedule.html", time_slots = time_slots, workshop_rooms_in_use = workshop_rooms_in_use, total_workshop_rooms=len(workshop_rooms_in_use), container_name = " ", jam_title = database.get_jam_details(database.get_current_jam_id()).name)


@public_routes.route("/static/files/<workshop_id>/<filename>")
@module_workshops_required
def files_download(workshop_id, filename):
    print("Hello world")
    file = database.get_file_for_download(workshop_id, "static/files/{}/{}".format(workshop_id, filename))
    login_status, user = logins.check_allowed(request, 3)
    if file.file_permission == "Public" or (file.file_permission == "Jam team only" and login_status):
        return send_file(file.file_path)
    else:
        abort(404)

@public_routes.route("/mozfest_import_workshops")
@module_core_required
def mozfest_import_workshops():
    import github_queries
    results = github_queries.get_github_project_data()
    workshops_available = database.get_workshops_to_select().all()
    for column in results:
        if column.name.startswith("#") or column.name.startswith("@") or "!all-day" in column.name:
            continue
        found_room = column.name.split("(")[0].strip()
        for card in column.cards:
            if card and card.attached_issue:
                workshop_found = False
                for workshop_available in workshops_available:
                    if workshop_available.workshop_title == card.attached_issue.title:
                        workshop_found = True
                        break
                if not workshop_found:
                    database.add_workshop(None, card.attached_issue.title, "N/A", 100, "Beginner", card.attached_issue.url, 0)


@public_routes.route("/mozfest_import")
@module_core_required
def mozfest_import():
    import github_queries
    results = github_queries.get_github_project_data()
    workshops = database.get_all_scheduled_workshops()
    rooms = database.get_workshop_rooms_objects()
    workshops_available = database.get_workshops_to_select()
    time_slots = database.get_time_slots_objects()
    for column in results:
        if column.name.startswith("#") or column.name.startswith("@") or "!all-day" in column.name:
            continue
        found_room_string = column.name.split("(")[0].strip()
        found_room = False
        for room in rooms:
            if room.room_name == found_room_string:
                found_room = room
                break
        if not found_room:
            continue
        
        
        for card in column.cards:
            if card and card.attached_issue:
                workshop_found = False
                for workshop_available in workshops_available:
                    if workshop_available.workshop_title == card.attached_issue.title:
                        workshop_found = workshop_available
                        break
                if workshop_found:
                    time_slot_found = False
                    time_slot_string = card.time.split("\r")[0].split(" ")[1]
                    for time_slot in time_slots:
                        if time_slot.slot_id == int(time_slot_string.replace("a", "").replace("b", "")):
                            time_slot_found = time_slot
                            
                            break
                    if time_slot_found:
                        database.add_workshop_to_jam_from_catalog(database.get_current_jam_id(), workshop_found.workshop_id, None, time_slot_found.slot_id, found_room.room_id, False)
                        print("I can add a {} to {} at {}".format(workshop_found.workshop_title, found_room.room_name, time_slot_found.slot_time_start))
    
    print()