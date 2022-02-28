from flask import Flask
from flask import render_template
from . import create_app


app = create_app()


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/legal')
def legal():
    return render_template('legal.html')


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run()
