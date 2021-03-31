from __future__ import print_function
import pickle
import os.path
import os
import string
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

list_char = ['?','"']


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
        print("Folder will be create: " + n_path)
        os.mkdir(n_path)

    except OSError:
        print("Creation of the directory %s failed" % n_path)
    else:
        print("Success")
    return n_path


def sort_f(f, number):
    try:
        result = sorted(f, key=operator.itemgetter(number))
        return result
    except IndexError as err:
        print("Cannot sort files/folders: ")
        print(err)


def isFolder(service, f_id):
    results = service.files().get(fileId=f_id,
                                  fields="id, name, size, mimeType").execute()

    if results['mimeType'] == "application/vnd.google-apps.folder":
        return True
    else:
        return results['name'], results['size']
        
        
def convert_string(str):
#    for char in string.punctuation:
#        str = str.replace(char, '_')
    for char in str:
        if char in list_char:
            str = str.replace(char,"_")
    return str


def get_id_in_folder(service, folder_id):
    results = service.files().list(q="'" + folder_id + "'" + " in parents",
                                   spaces='drive',
                                   pageSize=1000,
                                   fields="nextPageToken, files(id, name, mimeType, size)").execute()
    items = results.get('files', [])
    fld = 'folder'
    file = []
    folder = []
    if not items:
        print('No files found.')
    else:
        # print('Files:')
        for item in items:
            # print(item)
            if fld in item['mimeType']:
                folder.append([item['id'], item['name']])
                # print('Folder: ' + item['size'])
            else:
                file.append([item['id'], item['name'], item['size']])
                # print('File: ' + item['size'])

        folder = sort_f(folder, 1)
        file = sort_f(file, 1)

        print("Folders: ")
        for x in folder:
            print(x)

        print('Files: ')
        for y in (file):
            print(y)

    return file, folder


def download_file(service, file_id, name_org, size, path):
    name = convert_string(name_org)
    print("Download: " + "['" + file_id + "'" + ", '" + name + "']")
    dir = os.path.join(path, name)
    print(dir)
    # filesize =
    # print(str(filesize) + '....' + size)
    if os.path.exists(dir) == True and str(os.path.getsize(dir)) == size:
        print('File alreay exist, skipping...')
        return 0

    file_io_base = open(dir, 'wb')

    request = service.files().get_media(fileId=file_id)
    media_request = http.MediaIoBaseDownload(file_io_base, request)
    while True:
        try:
            status, done = media_request.next_chunk()
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
            return
        if status:
            print("... %d%%." % int(status.progress() * 100))
        if done:
            print('Download Complete')
            file_io_base.close()
            return 0


def download_folder(service, folder_id, path):
    # cur_path = os.getcwd()
    # os.mkdir(cur_path)
    # print(cur_path)
    files, folders = get_id_in_folder(service, folder_id)
    if len(files) != 0:
        for file in files:
            # print(file)
            # download_file(service, file[0], file[1])
            download_file(service, file[0], file[1], file[2], path)
    if len(folders) != 0:
        for folder in folders:
            # print(folder)
            n_path = create_folder(folder[1], path)
            print(n_path)
            download_folder(service, folder[0], n_path)


def main():
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
        name, size = isFolder(service, id)
        download_file(service, id, name, size, path1)


if __name__ == '__main__':
    main()
