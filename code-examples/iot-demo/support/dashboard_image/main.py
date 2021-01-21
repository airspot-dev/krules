from flask import Flask, render_template, request
import os


class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='%%',
        variable_end_string='%%',
        comment_start_string='<#',
        comment_end_string='#>',
    ))


app = CustomFlask(__name__)
app.config['DEBUG'] = False


@app.route("/")
def index():
    return render_template(
        "index.html",
        api_key=os.environ.get("PUSHER_APIKEY"),
        fleet_name=os.environ.get("FLEET_NAME"),
        fleet_channel=os.environ.get("FLEET_CHANNEL"),
        device_event=os.environ.get("DEVICE_DATA_EVENT")
    )


if __name__ == "__main__":
    app.run(use_debugger=True, use_reloader=True)
