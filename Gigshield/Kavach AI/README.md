# GigShield — Setup Guide

## Step 1: Install Python packages
```
pip install flask mysql-connector-python
```

## Step 2: Set up MySQL
1. Download and install XAMPP (https://www.apachefriends.org/)
2. Start Apache + MySQL in XAMPP Control Panel
3. Open phpMyAdmin → http://localhost/phpmyadmin
4. Click "New" → create database named `gigshield`
5. Click on `gigshield` → go to SQL tab → paste contents of schema.sql → click Go

## Step 3: Run the app
```
python app.py
```
Open browser → http://localhost:5000

## Flow to demo:
1. Go to /register → fill form → click Register → see AI premium → click Activate Policy
2. Note your Worker ID (shown in the success message)
3. Go to /policy → enter Worker ID → see your active policy
4. Go to /claims → enter Worker ID + city → click Check Now → see disruption signals + auto claim
