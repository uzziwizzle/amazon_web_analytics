from genericpath import isdir
from typing import Dict
from flask import Flask, render_template, request, redirect, url_for, flash,jsonify, json,send_file
from werkzeug.routing import IntegerConverter
from wtforms.fields.html5 import DateField
from dbhelper import DBHelper
from passwordhelper import PasswordHelper
from flask_login import LoginManager, login_required, login_user, logout_user, login_required, current_user
from user import User
from flask_uploads import configure_uploads, UploadSet, DOCUMENTS
from flask_mail import Mail, Message
from datetime import datetime, timedelta, date
import requests
import json


import pymongo
import glob
import os.path
import csv
import config
import datetime as de
import emails
import zipfile
import pandas as pd
from pandas import DataFrame, Series
from datetime import datetime, date
import openpyxl

app = Flask(__name__)

DB = DBHelper()
PH = PasswordHelper()
login_manager = LoginManager(app)

app.secret_key = config.secret_key


# Set path for documents upload and restrict files to certain file types
app.config['UPLOADED_DOCUMENTS_DEST'] = "upload"
app.config['UPLOADED_DOCUMENTS_ALLOW'] = ['xlsx']
docs = UploadSet('documents', DOCUMENTS)
configure_uploads(app, docs)

env = "TESTING" 

app.config.update(
    DEBUG=True,
    MAIL_SERVER = config.mail_server,
    MAIL_PORT = config.mail_port,
    MAIL_USE_TLS = False,
    MAIL_USE_SSL = True,
    MAIL_USERNAME = config.mail_username,
    MAIL_PASSWORD = config.mail_password,
    MAIL_SUPPRESS_SEND = False,
    MAIL_DEFAULT_SENDER=config.mail_username,
    TESTING = False
    )

recepients = config.recepient

# Instantiate Email
mail = Mail(app)

project_dir = os.path.abspath(os.path.dirname(__file__))

@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=['GET','POST'])
def login():
    if request.method=="POST":
        email=request.form["email"]
        password=request.form["password"]
        stored_user = DB.get_user(email)
        if stored_user and PH.validate_password(password, stored_user['salt'], stored_user['hashed']):
            user = User(email)
            login_user(user, remember=True)
            return redirect(url_for('recommendations'))
        return render_template("/page-login.html", msg1="Email or password invalid")
    return render_template("/page-login.html")



@app.route("/signup", methods=["GET", "POST"])
def register():
    if request.method=="POST":
        email=request.form["email"]
        phone=request.form["phone"]
        password=request.form["password"]
        if DB.get_user(email):
            return render_template("page-register.html", emailerror="Email address already registered")
        elif DB.get_user_by_phone(phone):
            return render_template("page-register.html", phone="phone already exists")
        salt = PH.get_salt()
        hashed = PH.get_hash((password + str(salt)).encode('utf-8'))
        DB.add_user(email, salt, hashed, phone)
        return redirect(url_for("login"))
    return render_template("page-register.html")


@app.route("/recommendations", methods=['GET','POST'])
def recommendations():
    if request.method=="POST":
        dfProductTemplate = pd.DataFrame(columns = ['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Ad Group', 'Max Bid', 'Keyword or Product Targeting', 'Product Targeting ID', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS'])
        filename = request.files["excel"]
        country = request.form["country"]
        pd.set_option('display.max_rows', 1000)

        # Create empty product templates dataframe
        dfProductTemplate = pd.DataFrame(columns = ['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Ad Group', 'Max Bid', 'Keyword or Product Targeting', 'Product Targeting ID', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS'])

        bulkFile = './{}/{}'.format(country, filename)
        bulkfileOpen_ = pd.read_excel(filename, sheet_name='Sponsored Products Campaigns')
        toProcess = ['Keyword', 'Product Targeting']
        bulkfileOpen = bulkfileOpen_[bulkfileOpen_['Record Type'].isin(toProcess)]

        # Convert percentages to float
        bulkfileOpen['ACoS'] = bulkfileOpen['ACoS'].str.rstrip('%').astype('float') / 100.0

        # Filter ACos greater than 30% -- lower bid
        highACoS = bulkfileOpen[bulkfileOpen['ACoS'] > 0.5]
        highACoS['Action'] = 'High ACoS; Consider lowering bid'
        dfProductTemplate = dfProductTemplate.append(highACoS)


        # Filter low ACoS KW - 10% -- increase bid
        lowACoS = bulkfileOpen[(bulkfileOpen['ACoS'] < 0.15) & (bulkfileOpen['Clicks'] > 10) & (bulkfileOpen['Sales'] > 0)]
        lowACoS['Action'] = 'Low ACoS; Consider increasing bid'
        dfProductTemplate = dfProductTemplate.append(lowACoS)


        # High clicks and no sales - reduce bid or delete keyword
        highClicksNoSale = bulkfileOpen[(bulkfileOpen['Clicks'].astype('int') > 10) & (bulkfileOpen['Orders'] == 0) & (bulkfileOpen['Spend'] > 5)]
        highClicksNoSale['Action'] = 'No sales; Consider lowering bid or deleting KW'
        dfProductTemplate = dfProductTemplate.append(highClicksNoSale)

        # High bid KW
        bulkfileOpen['CPC'] = bulkfileOpen['Spend'] / bulkfileOpen['Clicks']
        bulkfileOpen['CPC'] = bulkfileOpen['CPC'].fillna(0)
        highBidKW = bulkfileOpen[(bulkfileOpen['CPC'] > 0.8)]
        highBidKW['Action'] = 'High bid keyword. Reduce bid'
        dfProductTemplate = dfProductTemplate.append(highBidKW)

        # Rearrange column
        dfProductTemplate = dfProductTemplate.sort_values('Spend', ascending = False)[['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Ad Group', 'Max Bid', 'Keyword or Product Targeting', 'Product Targeting ID', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS', 'Action']]

        dfProductTemplate.fillna("", inplace = True)

        dfProductTemplate = dfProductTemplate.groupby(['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Ad Group', 'Max Bid', 'Keyword or Product Targeting', 'Product Targeting ID', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS'])['Action'].apply(','.join).reset_index()
        dfProductTemplate = dfProductTemplate.astype(str)
        dfProductTemplate_SP = dfProductTemplate.copy()

        # SB
        # Create empty product templates dataframe
        dfProductTemplate = pd.DataFrame(columns = ['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Ad Group', 'Max Bid', 'Keyword or Product Targeting', 'Product Targeting ID', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS'])

        bulkfileOpen_ = pd.read_excel(filename, sheet_name='Sponsored Brands Campaigns')

        toProcess = ['Keyword']
        bulkfileOpen = bulkfileOpen_[bulkfileOpen_['Record Type'].isin(toProcess)]

        # Convert percentages to float
        bulkfileOpen['ACoS'] = bulkfileOpen['ACoS'].str.rstrip('%').astype('float') / 100.0

        # Filter ACos greater than 50% -- lower bid
        highACoS = bulkfileOpen[bulkfileOpen['ACoS'] > 0.5]
        highACoS['Action'] = 'High ACoS; Consider lowering bid'
        dfProductTemplate = dfProductTemplate.append(highACoS)

        # Filter low ACoS KW - 10% -- increase bid
        lowACoS = bulkfileOpen[(bulkfileOpen['ACoS'] < 0.15) & (bulkfileOpen['Clicks'] > 10) & (bulkfileOpen['Sales'] > 0)]
        lowACoS['Action'] = 'Low ACoS; Consider increasing bid'
        dfProductTemplate = dfProductTemplate.append(lowACoS)

        # High clicks and no sales - reduce bid or delete keyword
        highClicksNoSale = bulkfileOpen[(bulkfileOpen['Clicks'].astype('int') > 15) & (bulkfileOpen['Orders'] == 0) & (bulkfileOpen['Spend'] > 5)]
        highClicksNoSale['Action'] = 'No sales; Consider lowering bid or deleting KW'
        dfProductTemplate = dfProductTemplate.append(highClicksNoSale)

        # High bid KW
        bulkfileOpen['CPC'] = bulkfileOpen['Spend'] / bulkfileOpen['Clicks']
        bulkfileOpen['CPC'] = bulkfileOpen['CPC'].fillna(0)
        highBidKW = bulkfileOpen[(bulkfileOpen['CPC'] > 0.8)]
        highBidKW['Action'] = 'High bid keyword. Reduce bid'
        dfProductTemplate = dfProductTemplate.append(highBidKW)

        if country == 'US':
            # Rearrange column
            dfProductTemplate = dfProductTemplate.sort_values('Spend', ascending = False)[['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Campaign Type', 'Budget', 'Portfolio ID', 'Campaign Start Date',	'Campaign End Date','Budget Type', 'Landing Page Url', 'Landing Page ASINs', 'Brand Name', 'Brand Entity ID', 'Brand Logo Asset ID', 'Headline', 'Creative ASINs', 'Automated Bidding', 'Bid Multiplier', 'Ad Group', 'Max Bid', 'Keyword', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS', 'Action']]

        elif country == 'CA':
            dfProductTemplate = dfProductTemplate.sort_values('Spend', ascending = False)[['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Campaign Type', 'Budget', 'Portfolio ID', 'Campaign Start Date',	'Campaign End Date','Budget Type', 'Landing page URL', 'Landing page ASINs', 'Brand name', 'Brand Entity ID', 'Brand logo asset ID', 'Headline', 'Creative ASINs', 'Automated Bidding', 'Bid Multiplier', 'Ad Group', 'Max Bid', 'Keyword', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS', 'Action']]

        elif country == 'UK':
            # Rearrange column
            dfProductTemplate = dfProductTemplate.sort_values('Spend', ascending = False)[['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Campaign Type', 'Budget', 'Portfolio ID', 'Campaign Start Date',	'Campaign End Date','Budget Type', 'Landing page URL', 'Landing page ASINs', 'Brand Name', 'Brand Entity ID', 'Brand logo asset ID', 'Headline', 'Creative ASINs', 'Automated Bidding', 'Bid Multiplier', 'Ad Group', 'Max Bid', 'Keyword', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS', 'Action']]


        dfProductTemplate.fillna("", inplace = True)

        if country == 'US' and 'CA':
            dfProductTemplate = dfProductTemplate.groupby(['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Campaign Type', 'Budget', 'Portfolio ID', 'Campaign Start Date',	'Campaign End Date','Budget Type', 'Landing Page Url', 'Landing Page ASINs', 'Brand Name', 'Brand Entity ID', 'Brand Logo Asset ID', 'Headline', 'Creative ASINs', 'Automated Bidding', 'Bid Multiplier', 'Ad Group', 'Max Bid', 'Keyword', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS'])['Action'].apply(','.join).reset_index()

        elif country == 'UK':
            dfProductTemplate = dfProductTemplate.groupby(['Record ID', 'Record Type', 'Campaign ID', 'Campaign', 'Campaign Type', 'Budget', 'Portfolio ID', 'Campaign Start Date',	'Campaign End Date','Budget Type', 'Landing page URL', 'Landing page ASINs', 'Brand Name', 'Brand Entity ID', 'Brand logo asset ID', 'Headline', 'Creative ASINs', 'Automated Bidding', 'Bid Multiplier', 'Ad Group', 'Max Bid', 'Keyword', 'Match Type', 'Campaign Status', 'Ad Group Status', 'Status', 'Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'ACoS'])['Action'].apply(','.join).reset_index()

        dfProductTemplate = dfProductTemplate.astype(str)

        dfProductTemplate_SB = dfProductTemplate.copy()
        dirName=project_dir+"/data/recommendations/{}".format(country)
        try:
            os.makedirs(dirName)    
            print("Directory " , dirName ,  " Created ")
        except FileExistsError:
            print("Directory " , dirName ,  " already exists")  
        with pd.ExcelWriter(project_dir+"/data/recommendations/{}/recommendations for {}.xlsx".format(country,date.today())) as writer:
            dfProductTemplate_SB.to_excel(writer, sheet_name='Sponsored Brand')
            dfProductTemplate_SP.to_excel(writer, sheet_name='Sponsored Product')
            
        return render_template("page-recommendations.html",link=country+'/recommendations for {}.xlsx'.format(date.today()),filename='recommendations for {}.xlsx'.format(date.today()),hide="")
    return render_template("page-recommendations.html",hide="d-none")
    

@app.route("/download/<c>/<link>")
def download(c,link):

    path=project_dir+"/data/recommendations/"+c+"/"+link
    return send_file(path, as_attachment=True)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))

@login_manager.user_loader
def load_user(user_id):
    user_password = DB.get_user(user_id)
    if user_password:
        return User(user_id)

if __name__ == "__main__":
    app.run()


