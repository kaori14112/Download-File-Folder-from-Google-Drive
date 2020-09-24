## This is script allow you to download file / folder from google just by it's ID (no compressed)
## How to use?
#### Install requirements libs for python: pip3 install -r .requirements --user
#### Enable google drive API and get credential json file (or you can create by your own): https://developers.google.com/drive/api/v3/quickstart/python
#### Put json file on a same folder at script
 
#### Just typing this command to upload files: python3 download.py -id xxxxxxxxx -f xxxx

- id : id of file or folder, go to Google drive, and go to folder that your want to download, folder id is on address bar, ex: https://drive.google.com/drive/u/0/folders/1sWlBT47osdfsdfKsdfsdfsdfybpDxL , then id is: 1sWlBT47osdfsdfKsdfsdfsdfybpDxL

- f: this is subfolder you want to download all file into (instead download files / folder on the same folder as script, i decided to create subfolder to store it. I can make it download to custom location - maybe someday, lazy af ^^)
