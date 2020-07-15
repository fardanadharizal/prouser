from flask import Flask, flash, render_template, json, request, redirect, url_for, session, send_from_directory
from flask_mysqldb import MySQL,MySQLdb
from markupsafe import escape
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import datetime
import qrcode
import cv2
import shutil
import bcrypt
import os

IMG_FOLDER = os.path.join('static', 'images')

app = Flask(__name__)
app.config['SECRET_KEY'] = '^A%DJAJU^JJ123'
app.config['MYSQL_HOST'] = 'haloryan.com'
app.config['MYSQL_USER'] = 'u6049187_nisahr'
app.config['MYSQL_PASSWORD'] = 'nisahr'
app.config['MYSQL_DB'] = 'u6049187_nisahr'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)


dt = datetime.datetime.now()
datenow = dt.strftime("%x")
timenow = dt.strftime("%X")
daynow = dt.strftime("%A")


@app.route("/")
def main():
    if session.get('id'):
        if session['level'] == 'mhs':
            curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            curl.execute("SELECT * FROM absen_mhs WHERE idm="+str(session['id']))
            data = curl.fetchall()
            curl.close()
            return render_template('home.html', data = data)
        else:
            curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            curl.execute("SELECT * FROM absen_dosen WHERE id_dosen="+str(session['id']))
            data = curl.fetchall()
            curl.close()
            return render_template('home.html', data = data)
    else:
        return redirect(url_for('masuk'))


@app.route("/create", methods=["GET", "POST"])
def create():
    if session.get('id'):
        if session['level'] == 'dosen':
            if request.method == 'GET':
                day = daynow.lower()
                curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                curl.execute("SELECT * FROM hari WHERE day=%s",(day,))
                hari = curl.fetchone()
                curl.close()

                _curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                _curl.execute("SELECT * FROM jadwal WHERE id_dosen=%s AND hari=%s",(session['id'], hari['hari']))
                jadwal = _curl.fetchall()
                _curl.close()

                return render_template('mulaikelas.html', jadwal = jadwal)
            else:
                _kelas = request.form['inputKelas']
                jadwal = _kelas.split(',')

                idj = jadwal[0]
                kelas = jadwal[2]
                matkul = jadwal[3]
                kode = jadwal[4]
                step = jadwal[6]
                status = 'running'

                curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                curl.execute("SELECT * FROM absen_dosen WHERE tgl=%s AND id_jadwal=%s",(datenow,idj))
                get = curl.fetchall()
                curl.close()
                if not get:
                    _curl = mysql.connection.cursor()
                    _curl.execute("INSERT INTO absen_dosen (tgl, id_jadwal, id_dosen, nama_dosen, kelas, matkul, mulai, status, kode, step) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",(datenow, idj, session['id'], session['nama'], kelas, matkul, timenow, status, kode, step))
                    mysql.connection.commit()
                    flash('Yeay, kelas berhasil dimulai', 'success')
                    return redirect(url_for('main'))
                else:
                    flash('Hmm, kamu sudah menghadiri kelas ini', 'error')
                    return redirect(url_for('main'))
        else:
            return redirect(url_for('main'))
    else:
        return redirect(url_for('masuk'))


@app.route('/stop/<path:id>')
def delete(id):
    if session.get('id'):
        if session['level'] == 'dosen':
            curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            curl.execute("UPDATE absen_dosen SET selesai=%s, status=%s WHERE id=%s",(timenow,'finished',id))
            cek = curl.fetchall()
            curl.close()
            flash('Yeay, kelas kamu sudah berakhir', 'success')
            return redirect(url_for('main'))
        else:
            return redirect(url_for('main'))
    else:
        return redirect(url_for('masuk'))


@app.route("/qr/<path:id>")
def qr(id):
    if session.get('id'):
        if session['level'] == 'dosen':
            curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            curl.execute("SELECT * FROM qr WHERE idj=%s",(id,))
            get = curl.fetchone()
            curl.close()
            if not get:
                data = id
                filename = str(id)+"qr.png"
                img = qrcode.make(data)
                img.save(filename)
                shutil.move(filename, 'static/images')

                _curl = mysql.connection.cursor()
                _curl.execute("INSERT INTO qr (idj, pic) VALUES (%s, %s)",(id,filename))
                mysql.connection.commit()

                return render_template('qr.html', qrpic = filename, id = id)
            else:
                qrpic = get['pic']
                return render_template('qr.html', qrpic = qrpic, id = id)
        else:
            return redirect(url_for('main'))
    else:
        return redirect(url_for('masuk'))


@app.route("/scan")
def scan():
    if session.get('id'):
        if session['level'] == 'mhs':
            curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            curl.execute("SELECT * FROM absen_mhs WHERE tgl=%s AND idm=%s",(datenow, session['id']))
            get = curl.fetchone()
            curl.close()
            if get:
                idabsen = get['id']
                cap = cv2.VideoCapture(0)
                detector = cv2.QRCodeDetector()
                while True:
                    _, img = cap.read()
                    data, bbox, _ = detector.detectAndDecode(img)
                    if bbox is not None:
                        for i in range(len(bbox)):
                            cv2.line(img, tuple(bbox[i][0]), tuple(bbox[(i+1) % len(bbox)][0]), color=(255, 0, 0), thickness=2)
                        if data:
                            idj = data
                            _curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                            _curl.execute("SELECT * FROM absen_dosen WHERE id=%s",(idj,))
                            _get = _curl.fetchone()
                            _curl.close()
                            if _get:
                                step = _get['step']
                                sm = 'm'+step
                                m = sm.replace(' ','')
                                sj = 'j'+step
                                j = sj.replace(' ','')
                                __curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                                __curl.execute("UPDATE absen_mhs SET "+m+"=%s, "+j+"=%s WHERE id=%s",(_get['id'],timenow,idabsen,))
                                __cek = __curl.fetchall()
                                __curl.close()
                                flash('Yeay, absen berhasil', 'success')
                                return redirect(url_for('main'))
                            else:
                                return redirect(url_for('main'))
            else:
             _curl = mysql.connection.cursor()
             _curl.execute("INSERT INTO absen_mhs (tgl, idm, kelas, nama, nim) VALUES (%s, %s, %s, %s, %s)",(datenow, session['id'], session['kelas'], session['nama'], session['nim']))
             mysql.connection.commit()
             return redirect(url_for('scan'))
        else:
            return redirect(url_for('main'))
    else:
        return redirect(url_for('masuk'))



@app.route('/masuk', methods=["GET", "POST"])
def masuk():
    try:
        if session.get('id'):
            return redirect(url_for('main'))
        else:
            if request.method == 'GET':
                return render_template('masuk.html')
            else:
                _email = request.form['inputEmail']
                _password = request.form['inputPassword']
                _level = request.form['inputLv']
                if _email and _password and _level:
                    if _level == 'mhs':
                        curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                        curl.execute("SELECT * FROM mhs WHERE email=%s AND password=%s",(_email, _password))
                        user = curl.fetchone()
                        curl.close()
                        if user:
                            session['id'] = user['id']
                            session['kelas'] = user['kelas']
                            session['nim'] = user['nim']
                            session['nama'] = user['nama']
                            session['level'] = 'mhs'
                            return redirect(url_for('main'))
                        else:
                            flash('Oops, data tidak ditemukan. Coba cek kredensial kamu', 'error')
                            return redirect(url_for('masuk'))
                    else:
                        curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                        curl.execute("SELECT * FROM dosen WHERE email=%s AND password=%s",(_email, _password))
                        user = curl.fetchone()
                        curl.close()
                        if user:
                            session['id'] = user['id']
                            session['level'] = 'dosen'
                            session['nama'] = user['nama']
                            return redirect(url_for('main'))
                        else:
                            flash('Oops, data tidak ditemukan. Coba cek kredensial kamu', 'error')
                            return redirect(url_for('masuk'))
                else:
                    flash('Hmm, kamu harus melengkapi seluruh data sebelum masuk', 'error')
                    return redirect(url_for('masuk'))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('masuk'))


@app.route('/keluar')
def keluar():
    session.clear()
    return redirect(url_for('masuk'))


if __name__ == "__main__":
    app.run(debug=True)
