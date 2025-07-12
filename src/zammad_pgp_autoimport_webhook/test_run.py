from flask import Flask

app = Flask(__name__)


@app.route("/status")
def status():
    breakpoint()
    return {"status": "ok"}


if __name__ == '__main__':
    app.run()
