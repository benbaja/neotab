from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from markupsafe import escape
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth
from benchling_client import getContainerDB, mark_opened_benchling, archive_container, move_container
from order_tracker import post_order_tracker
from datetime import date
import requests as py_req
from pdf2image import convert_from_bytes
import sys
import os
import pandas as pd

app = Flask(__name__)
SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
# uses flask_session to get server-side session cookies and load the database in it. Allows to pass the db between routes even after refresh ;-)
Session(app)
app.config['BOOTSTRAP_BTN_STYLE'] = 'primary'
USE_TEST_INSTANCE = os.environ["USE_TEST_INSTANCE"]

running_path = os.path.dirname(os.path.abspath(sys.argv[0]))

if USE_TEST_INSTANCE=='True' :
    benchling_auth = Benchling(url="https://neoplantstest.benchling.com/", auth_method=ApiKeyAuth(os.environ["BL_TEST_TOKEN"]))
else :
    benchling_auth = Benchling(url="https://neoplants.benchling.com/", auth_method=ApiKeyAuth(os.environ["BL_TOKEN"]))

@app.route("/")
def index():
    session["prev_URL"] = "/"
    if session.get("containerDB", pd.DataFrame()).empty == True :
        return redirect('/refresh')
    return render_template("home.html", USE_TEST_INSTANCE=USE_TEST_INSTANCE)

@app.route('/consumables/<cont_id>')
def consumables(cont_id):
    containerDB = session.get("containerDB")
    if session.get("containerDB", pd.DataFrame()).empty == False :
        if cont_id in containerDB.index.values.tolist() :
            # store URL in session so the page does not change in case of DB refresh
            session["prev_URL"] = "/consumables/" + str(cont_id)

            # access DB row for container barcode
            session["cont_metadata"] = containerDB.loc[cont_id]

            # check for alert signals in the session variables to display
            alert = session.pop("alert", None)

            today_date = date.today().strftime("%Y-%m-%d")

            # loads the template with metadata extracted from the db 
            return render_template("container.html", entity_type="consumable", metadata_dict=session["cont_metadata"], alert=alert, USE_TEST_INSTANCE=USE_TEST_INSTANCE, today_date=today_date) # TO CHANGE WITH DYNAMIC ENTITY TYPE LATER
    if session.get("prev_URL") :
        return redirect(session.pop('prev_URL', None))
    return redirect('/')

@app.route('/search', methods=["GET", "POST"])
def search():
    cont_id = request.form.get("searchBar")
    containerDB = session.get("containerDB")
    if session.get("containerDB", pd.DataFrame()).empty == False :
        if cont_id in containerDB.index :
            return redirect(url_for('consumables', cont_id=cont_id))
    return redirect('/')
    
@app.route("/refresh", methods=["GET", "POST"])
def refresh():
    session.pop('containerDB', None)
    session["containerDB"] = getContainerDB(benchling_auth, USE_TEST_INSTANCE)
    if session.get("prev_URL") :
        return redirect(session.pop('prev_URL', None))
    return redirect('/')

@app.route("/request", methods=["GET", "POST"])
def ot_request():
    req_dict = {
        "name": session["cont_metadata"].get("name"),
        "supplier": session["cont_metadata"].get("supplier"),
        "ref": session["cont_metadata"].get("ref"),
        "quantity": request.form.get("request-quantity", 1)
    }
    ot_response = post_order_tracker(req_dict)

    # pass the alert signal to session to warn user of success state
    if ot_response == 200 :
        session["alert"] = "req_success"
    else :
        session["alert"] = "req_failed"

    if session.get("prev_URL") :
        return redirect(session.pop('prev_URL', None))
    return redirect('/')

@app.route("/opened", methods=["GET", "POST"])
def mark_opened():
    date_opened = request.form.get("date-opened")
    cont_id = session["cont_metadata"].get("id")
    if date_opened :
        marked_open = mark_opened_benchling(benchling_auth, cont_id, date_opened)
    else :
        marked_open = False

    if marked_open :
        session["alert"] = "open_success"
        # "cheats" by updating the cached db directly to prevent a long refresh each time
        barcode = session["cont_metadata"].name
        session["containerDB"].at[barcode, "opened"] = date_opened
        session["cont_metadata"]["opened"] = date_opened
    else :
        session["alert"] = "open_failed"

    if session.get("prev_URL") :
        return redirect(session.pop('prev_URL', None))
    return redirect('/')

@app.route("/emptied", methods=["GET", "POST"])
def mark_empty():
    cont_id = session["cont_metadata"].get("id")

    marked_empty = archive_container(benchling_auth, cont_id)

    if marked_empty :
        session["alert"] = "empty_success"
        # "cheats" by updating the cached db directly to prevent a long refresh each time
        barcode = session["cont_metadata"].name
        session["containerDB"].at[barcode, "archived"] = True
        session["cont_metadata"]["archived"] = True
    else :
        session["alert"] = "empty_failed"

    if session.get("prev_URL") :
        return redirect(session.pop('prev_URL', None))
    return redirect('/')

@app.route("/moved", methods=["GET", "POST"])
def move_location():
    cont_id = session["cont_metadata"].get("id")
    location_barcode = request.form.get("move-location-bcode")

    marked_empty = move_container(benchling_auth, cont_id, location_barcode)

    if marked_empty :
        session["alert"] = "move_success"
    else :
        session["alert"] = "move_failed"

    if session.get("prev_URL") :
        return redirect(session.pop('prev_URL', None))
    return redirect('/')

@app.route("/msds", methods=["GET", "POST"])
def display_msds():
    if session.get("cont_metadata").empty == False :
        blob_fr = session["cont_metadata"].get("msds_fr")
        pages_dict_fr = {}
        if blob_fr :
            # generates download URL for blob (file storage system on Benchling), generated links are only available for 1h
            url_fr = benchling_auth.blobs.download_url(blob_fr).download_url
            r = py_req.get(url_fr,allow_redirects=True)

            # due to PDFs being hard to display on old browsers, individual pages are rendered to images and sthen displayed on the "carrousel"
            images_fr = convert_from_bytes(r.content)

            count = 1
            for i in images_fr :
                path = "static/msds/fr/"+str(count)+".jpg"
                i.save(path)
                pages_dict_fr[count] = path
                count += 1

        blob_en = session["cont_metadata"].get("msds_en")
        pages_dict_en = {}
        if blob_en :
            url_en = benchling_auth.blobs.download_url(blob_en).download_url
            r = py_req.get(url_en,allow_redirects=True)

            images_en = convert_from_bytes(r.content)

            count = 1
            for i in images_en :
                path = "static/msds/en/"+str(count)+".jpg"
                i.save(path)
                pages_dict_en[count] = path
                count += 1    

        if pages_dict_en or pages_dict_fr :
            return render_template("msds.html", pages_dict_fr=pages_dict_fr, pages_dict_en=pages_dict_en, entity_name=session["cont_metadata"].get("name"))
        else :
            return redirect(session.pop('prev_URL', None))
    else :
        redirect('/')