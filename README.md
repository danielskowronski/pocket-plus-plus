# Pocket++ `[work-in-progress]`
A web-app to extend Mozilla's Pocket for people dealing with dozens of saved content. 

Main features include:
* full list of saved (not archived) articles in form of sortable table
* time and count statistics - to track progress of reading and/or saving new stuff
  * idea that'll be implemented later: track count and time changes in InfluxDB
* random article selection - when you just can't decide

![Demo of application](demo.png)

## Installation
```
python3 -m pip install -r requirements.txt
```

## Config
You must use `config.yml` looking like this:

```
---
app_cfg:
  debug: true
  port: 8080
  consumer_key: '$TOKEN'
  redirect_uri: 'http://localhost:8080/callback'

```

You need `$TOKEN` being *consumer key* from https://getpocket.com/developer/apps/

## Usage
```
python3 ppp.py
```

## Development
You may want to use below syntax to skip getpocket.com authorization every time you restart app (or after it's autorestarted by CherryPy):
```
python3 ppp.py $REQUEST_TOKEN $ACCESS_TOKEN
```
`$REQUEST_TOKEN` and `$ACCESS_TOKEN` can be found in application log when `debug: true`.
