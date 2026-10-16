"""Intentionally broken demo site for ProofLoop. Contains no secrets."""
import os

from flask import Flask, render_template, request

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/contact")
def contact():
    return render_template("contact.html")


@app.post("/contact")
def contact_submit():
    name = request.form.get("name", "").strip() or "friend"
    return render_template("success.html", name=name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "3000")))
