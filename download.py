from __future__ import print_function
import pickle
import os.path
import os
import string
import hashlib
from datetime import datetime
import time

import asyncio
import aiohttp

# import io
from argparse import ArgumentParser
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# from googleapiclient.http import MediaIoBaseDownload
from apiclient import http
from apiclient import errors
import operator

SCOPES = ['https://www.googleapis.com/auth/drive']

list_char = ['\\', '//', '|', '*', '?', '<', '>']

list_download_file = []

def parse_args():
    """
                Parse arguments
        """

    parser = ArgumentParser(
        description="Download folder from Google Drive")
    parser.add_argument('-id', '--ID', type=str,
                        help='ID of folder')
    parser.add_argument('-f', '--localfolder', type=str,
                        help='Local folder')

    return parser.parse_args()


def logging(log, level=0):
    curr_time = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
    if level == 0:
        print(curr_time + "[INFO] " + log)
    elif level == 1:
        print(curr_time + "[WARN] " + log)
    elif level == 2:
        print(curr_time + "[CRIT] " + log)

def authentication():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_console()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def create_folder(name, path):
    try:
        n_path = os.path.join(path, name)
        #print("Folder will be create: " + n_path)
        logging("Folder will be create: %s" % n_path)
        if os.path.exists(n_path):
            logging("Directory already exist")
            return n_path
        else:
            os.mkdir(n_path)
    except OSError:
        logging("Directory %s failed to create... Maybe it already exist" % n_path, 1)
    else:
        logging("Directory created.")
    return n_path


def sort_f(f, number):
    try:
        result = sorted(f, key=operator.itemgetter(number))
        return result
    except IndexError as err:
        logging("Cannot sort files/folders: ", 2)
        logging(str(err), 2)


def checkmd5(file_path):
    # Calculate the MD5 checksum of the file
    md5_hash = hashlib.md5()
    if (os.path.isfile(file_path)):
        with open(file_path, "rb") as file:
            # Read the file in small chunks to save memory
            for chunk in iter(lambda: file.read(4096), b""):
                md5_hash.update(chunk)
            
        return md5_hash.hexdigest()
    else:
        return "hash_not_found"


def isFolder(service, f_id):
    results = service.files().get(fileId=f_id,
                                  fields="id, name, md5Checksum, mimeType").execute()

    if results['mimeType'] == "application/vnd.google-apps.folder":
        return True
    else:
        return results['name'], results['md5Checksum']
        
        
def convert_string(str):
#    for char in string.punctuation:
#        str = str.replace(char, '_')
    for char in str:
        if char in list_char:
            str = str.replace(char,"_")
        if char == "'":
            str = str.replace(char,";")
        if char == '"':
            str = str.replace(char,"'")
    return str
    
    
def humanbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
   B = float(B)
   KB = float(1024)
   MB = float(KB ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776

   if B < KB:
      return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f} MB'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)
      
def convert_size_to_bytes(size_str):
    # Split the string into parts (e.g., "0.0" and "Byte")
    parts = size_str.split()
    
    # Check if the parts contain a valid number and unit
    if len(parts) != 2 or not parts[0].replace('.', '', 1).isdigit():
        raise ValueError("Invalid file size format")
    
    # Extract the numerical part and convert it to a float
    size_num = float(parts[0])
    
    # Define a dictionary to map units to bytes
    size_units = {
        "Byte": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
        "PB": 1024**5,
        "EB": 1024**6,
        "ZB": 1024**7,
        "YB": 1024**8
    }
    
    # Get the unit and convert the size to bytes
    size_unit = parts[1]
    if size_unit in size_units:
        size_in_bytes = int(size_num * size_units[size_unit])
        return size_in_bytes
    else:
        raise ValueError("Invalid file size unit")


def get_id_in_folder(service, folder_id):
    results = service.files().list(q="'" + folder_id + "'" + " in parents",
                                   spaces='drive',
                                   pageSize=1000,
                                   fields="nextPageToken, files(id, name, mimeType, md5Checksum)").execute()
    items = results.get('files', [])
    fld = 'folder'
    file = []
    folder = []
    if not items:
        logging('Folder is empty, no files found. Skipping...')
    else:
        # print('Files:')
        for item in items:
            # print(item)
            if fld in item['mimeType']:
                folder.append([item['id'], item['name']])
                # print('Folder: ' + item['size'])
            else:
                #size = humanbytes(item['size'])
                #file.append([item['id'], item['name'], size])
                md5_checksum = item.get('md5Checksum', 'md5 of %s is not available from API' % {item['name']})
                file.append([item['id'], item['name'], md5_checksum])
                # print('File: ' + item['size'])

        folder = sort_f(folder, 1)
        file = sort_f(file, 1)

        if len(folder) != 0:
            logging("List folders: ")
            for x in folder:
                print(x[1])
        if len(file) != 0:
            index1 = 1
            logging('List files in parent folder: [%s]' % folder_id)
            for y in (file):
                print("%s: %s" % (str(index1), y[1]))
                index1+=1
        else:
            logging('List file empty')
    return file, folder


async def download_file(service, file_id, name_org, md5Checksum, path):
    #original_directory = os.getcwd()
    name = convert_string(name_org)
    logging("File name: ['" + name + "'] - ID: ['" + file_id + "']")
    dir = os.path.join(path, name)
    # filesize =
    # print(str(filesize) + '....' + size)
    #print(dir)
    #print(os.path.exists(path))
    #print(os.path.isfile(dir))
    #print(str(checkmd5(dir)) + " - " + str(md5Checksum))
    if os.path.exists(dir) == True and str(checkmd5(dir)) == str(md5Checksum):
        logging('File alreay exist, skipping... \n')
        return 0

    #print("Path Length:", len(dir))
    #os.chdir(path)
    file_io_base = open(dir, 'wb')

    request = service.files().get_media(fileId=file_id)
    media_request = http.MediaIoBaseDownload(file_io_base, request)

    prev_progress = 0.0
    prev_time = time.time()

    while True:
        try:
            status, done = media_request.next_chunk()
        except errors.HttpError as error:
            logging('An error occurred: %s \n' % error, 2)
            return
        if status:
            current_time = time.time()
            elapsed_time = current_time - prev_time

            downloaded_bytes = status.resumable_progress
            total_bytes = status.total_size

            download_speed = (downloaded_bytes - prev_progress) / elapsed_time

            progress_message = "Current: %s / Total: %s - %.2f%% - Speed: %s/s" % (
                humanbytes(downloaded_bytes), humanbytes(total_bytes), status.progress() * 100, humanbytes(download_speed))

            padding = ' ' * (len(progress_message) + 2)

            print(padding, end="\r")
            print(progress_message, end="\r", flush=True)

            prev_progress = downloaded_bytes
            prev_time = current_time
        if done:
            logging('Download Complete! \n')
            file_io_base.close()
            break
  #  os.chdir(original_directory)        
    #return 0


def download_folder(service, folder_id, path):
    # cur_path = os.getcwd()
    # os.mkdir(cur_path)
    # print(cur_path)
    files, folders = get_id_in_folder(service, folder_id)
    if len(files) != 0:
        for file in files:
            # print(file)
            # download_file(service, file[0], file[1])
            #download_file(service, file[0], file[1], file[2], path)
            temp_list = [file[0], file[1], file[2], path]
            list_download_file.append(temp_list)
    if len(folders) != 0:
        for folder in folders:
            # print(folder)
            n_path = create_folder(folder[1], path)
            print(n_path)
            download_folder(service, folder[0], n_path)


# def handle_multi_download(service, list_download_file):
#     if len(list_download_file) == 0:
#         logging("Download list is empty!", 2)
#         exit(1)
    
async def download_files_concurrently(service, list_download_file):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for item in list_download_file:
            file_id, name, md5Checksum, path = item
            name = convert_string(name)
            dir = os.path.join(path, name)
            
            if os.path.exists(dir) and str(checkmd5(dir)) == str(md5Checksum):
                logging(f'File {name} already exists, skipping...')
            else:
                tasks.append(download_file(service, file_id, name, md5Checksum, path))

        if tasks:
            await asyncio.gather(*tasks)



async def main():
    args = parse_args()
    id = args.ID
    folder = args.localfolder

    creds = authentication()
    service = build('drive', 'v3', credentials=creds)
    #file, folder = get_id_in_folder(service, "'root'")
    path = os.getcwd()
    path1 = create_folder(folder, path)

    if isFolder(service,id) == True:
        download_folder(service, id, path1)
    else:
        name, md5Checksum = isFolder(service, id)
        download_file(service, id, name, md5Checksum, path1)
    

    print(list_download_file)
    await download_files_concurrently(service, list_download_file)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
