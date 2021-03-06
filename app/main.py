import os
import PIL
from PIL import Image
import simplejson
import traceback
import numpy
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, make_response
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
import multiprocessing

lock = multiprocessing.Lock()

import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image
from torn_detection.detection_api import detect_imagev2
from lib.upload_file import uploadfile

ALLOWED_EXTENSIONS = set(['jpg', 'mp4', 'zip'])

frequency = cv2.getTickFrequency()
app = Flask(__name__)
app.config.from_pyfile('config.py')
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'zip'])
IGNORED_FILES = set(['.gitignore'])

booststrap = Bootstrap(app)

fontpath = "./app/static/demo.ttc" # <== 这里是宋体路径

b,g,r,a = 0,0,255,0
@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('main.html')


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def gen_file_name(filename):
    """
    If file was exist already, rename it and return a new name
    """

    i = 1
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        name, extension = os.path.splitext(filename)
        filename = '%s_%s%s' % (name, str(i), extension)
        i += 1

    return filename

def create_thumbnail(image):
    try:
        base_width = 80
        img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], image))
        w_percent = (base_width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)
        img.save(os.path.join(app.config['THUMBNAIL_FOLDER'], image))

        return True

    except:
        print(traceback.format_exc())
        return False


@app.route("/upload_back", methods=['GET', 'POST'])
def upload_back():
    if request.method == 'POST':
        files = request.files['file']

        if files:
            filename = secure_filename(files.filename)
            filename = gen_file_name(filename)
            mime_type = files.content_type

            if not allowed_file(files.filename):
                result = uploadfile(name=filename, type=mime_type, size=0, not_allowed_msg="File type not allowed")

            else:
                # detect
                filestr = files.read()
                # convert string data to numpy array
                npimg = numpy.fromstring(filestr, numpy.uint8)
                # convert numpy array to image
                img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                def progress(image):
                    with lock:
                        ret, image = detect_imagev2(image)
                    h, w, _ = image.shape
                    import cv2
                    img_pil = Image.fromarray(image)
                    draw = ImageDraw.Draw(img_pil)
                    size = int(min(h, w) / 10)
                    print("3: ", size)
                    #font = ImageFont.truetype(fontpath, size)
                    global text_str
                    if ret:
                        text_str = "have"
                    else:
                        text_str = "no"
                    #draw.text((int(w / 8), int(h / 4)), text_str, font=font, fill=(b, g, r, a))
                    image = np.array(img_pil)

                    # image = cv2.putText(image, "{} Torn".format(ret), (0, 100), cv2.FONT_HERSHEY_COMPLEX, 2.0, (0, 255, 0), 5)
                    return text_str, image

                text_str, img = progress(img)
                filename = "{}_{}.jpg".format(filename.split(".")[0], text_str)

                # save file to disk
                uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                cv2.imwrite(uploaded_file_path, img)
               # files.save(uploaded_file_path)

                # create thumbnail after saving
                if mime_type.startswith('image'):
                    create_thumbnail(filename)

                # get file size after saving
                size = os.path.getsize(uploaded_file_path)

                # return json for js call back
                result = uploadfile(name=filename, type=mime_type, size=size)

            return simplejson.dumps({"files": [result.get_file()]})

    if request.method == 'GET':
        # get all file in ./data directory
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if
                 os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f)) and f not in IGNORED_FILES]

        file_display = []

        for f in files:
            size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], f))
            file_saved = uploadfile(name=f, size=size)
            file_display.append(file_saved.get_file())

        return simplejson.dumps({"files": file_display})

    return redirect(url_for('index'))

from ocrs.model import predict
@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        files = request.files['file']

        if files:
            filename = secure_filename(files.filename)
            filename = gen_file_name(filename)
            mime_type = files.content_type

            if not allowed_file(files.filename):
                result = uploadfile(name=filename, type=mime_type, size=0, not_allowed_msg="File type not allowed")

            else:
                # detect
                filestr = files.read()
                # convert string data to numpy array
                npimg = numpy.fromstring(filestr, numpy.uint8)
                # convert numpy array to image
                img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                def progress(image):
                    with lock:
                        img = Image.fromarray(image).convert("L")
                        ret = predict(img)
                        print(ret)
                        tmp = "image_"
                        for i in ret:
                            if i in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                                tmp+=i
                        ret = tmp+".jpg"
                    # image = cv2.putText(image, "{} Torn".format(ret), (0, 100), cv2.FONT_HERSHEY_COMPLEX, 2.0, (0, 255, 0), 5)
                    return ret, image

                text_str, img = progress(img)
                filename = text_str

                # save file to disk
                uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                cv2.imwrite(uploaded_file_path, img)
               # files.save(uploaded_file_path)

                # create thumbnail after saving
                if mime_type.startswith('image'):
                    create_thumbnail(filename)

                # get file size after saving
                size = os.path.getsize(uploaded_file_path)

                # return json for js call back
                result = uploadfile(name=filename, type=mime_type, size=size)

            return simplejson.dumps({"files": [result.get_file()]})

    if request.method == 'GET':
        # get all file in ./data directory
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if
                 os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f)) and f not in IGNORED_FILES]

        file_display = []

        for f in files:
            size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], f))
            file_saved = uploadfile(name=f, size=size)
            file_display.append(file_saved.get_file())

        return simplejson.dumps({"files": file_display})

    return redirect(url_for('index'))



@app.route("/delete/<string:filename>", methods=['DELETE'])
def delete(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file_thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)

            if os.path.exists(file_thumb_path):
                os.remove(file_thumb_path)

            return simplejson.dumps({filename: 'True'})
        except:
            return simplejson.dumps({filename: 'False'})


# serve static files
@app.route("/thumbnail/<string:filename>", methods=['GET'])
def get_thumbnail(filename):
    return send_from_directory(os.path.join(app.config['THUMBNAIL_FOLDER']), filename)
    #return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename=filename)


@app.route("/data/<string:filename>", methods=['GET'])
def get_file(filename):
    print("data/filename", filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename=filename)

@app.route('/dight', methods=['GET', 'POST'])
def DightDetection():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = file.filename
        #    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filestr = file.read()
            # convert string data to numpy array
            npimg = numpy.fromstring(filestr, numpy.uint8)
            # convert numpy array to image
            img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h,w,_=img.shape

            def progress(image):
                with lock:
                    img = Image.fromarray(image).convert("L")
                    ret = predict(img)
                    print(ret)
                    tmp = ""
                    for i in ret:
                        if i in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                            tmp += i
                    ret = tmp
                # image = cv2.putText(image, "{} Torn".format(ret), (0, 100), cv2.FONT_HERSHEY_COMPLEX, 2.0, (0, 255, 0), 5)
                return ret, image

            text_str, img = progress(img)
            print("rec: ", text_str)
            print("height: ",h)
            cv2.putText(img, text_str,(0,h), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255))
            cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            img_encode = cv2.imencode('.jpg', img)[1]
            # imgg = cv2.imencode('.png', img)

            data_encode = np.array(img_encode)
            # 返回图片
            #response = make_response(data_encode.tostring())
            #response.headers['Content-Type'] = 'image/png'
            import json
            data = {"result": text_str}
            response = make_response(json.dumps(data))
            response.headers["Content-Type"] = "application/json"
            return response
    #        return redirect(url_for('face_upload_img',filename=filename))
    return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form action="" method=post enctype=multipart/form-data>
        <p><input type=file name=file>
           <input type=submit value=Upload>
        </form>
        '''



@app.route('/torn', methods=['GET', 'POST'])
def tornDetection():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = file.filename
        #    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filestr = file.read()
            # convert string data to numpy array
            npimg = numpy.fromstring(filestr, numpy.uint8)
            # convert numpy array to image
            img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            def progress(image):
                ret, image = detect_imagev2(image)
                h,w,_ = image.shape
                import cv2
                img_pil = Image.fromarray(image)
                draw = ImageDraw.Draw(img_pil)
                size = int(min(h,w) / 10)
                print("3: " ,size)
                font = ImageFont.truetype(fontpath, size)
                if ret:
                    text_str = "包裹破损"
                else:
                    text_str = "没有破损"
                draw.text((int(w/8), int(h/4)), text_str, font=font, fill=(b,g,r,a))
                image = np.array(img_pil)

                #image = cv2.putText(image, "{} Torn".format(ret), (0, 100), cv2.FONT_HERSHEY_COMPLEX, 2.0, (0, 255, 0), 5)
                return image

            img = progress(img)

            img_encode = cv2.imencode('.jpg', img)[1]
            # imgg = cv2.imencode('.png', img)

            data_encode = np.array(img_encode)

            response = make_response(data_encode.tostring())
            response.headers['Content-Type'] = 'image/png'
            return response
    #        return redirect(url_for('face_upload_img',filename=filename))
    return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form action="" method=post enctype=multipart/form-data>
        <p><input type=file name=file>
           <input type=submit value=Upload>
        </form>
        '''

@app.route('/index', methods=['GET', 'POST'])
def upload_files():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port =8080, debug=False, threaded=True)
    #app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
