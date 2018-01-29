import uuid
from flask import Flask, render_template

import database as database
import configuration

from routes.api_routes import api_routes
from routes.public_routes import public_routes
from routes.attendee_routes import attendee_routes
from routes.admin_routes import admin_routes
from routes.misc_routes import misc_routes

app = Flask(__name__)
app.secret_key = str(uuid.uuid4()).replace("-", "")[:10]

app.register_blueprint(api_routes)
app.register_blueprint(public_routes)
app.register_blueprint(attendee_routes)
app.register_blueprint(admin_routes)
app.register_blueprint(misc_routes)

configuration.output_modules_enabled()


@app.teardown_appcontext
def shutdown_session(exception=None):
    database.db_session.remove()


@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.context_processor
def inject_modules():
    return dict(modules_enabled=configuration.verify_modules_enabled())

if __name__ == '__main__':
    app.run()
