import os
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.abspath('./uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET'])
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload():
    media_type = request.form['media-type']
    for i in range(len(request.files)):
        filename = f"{media_type}/{request.form[f'path-{i}']}"
        file = request.files[f'files[{i}]']

        if 'undefined' in filename:
            filename = f"{media_type}/{file.filename}"

        dirs = filename.split('/')
        if len(dirs) > 1:
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], "/".join(dirs[:-1])), exist_ok=True)


        if file and filename:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))


    return("Uploaded Files")