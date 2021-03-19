
from krules_flask_env import KRulesApp
from flask import Response, request

app = KRulesApp("webhook")


@app.route("/", methods=["POST"])
def main():
    pass

