import requests
import os
import time
from threading import Thread

try:
    from utils.JWT import JWT
    from utils.basedir import BASEDIR
except ImportError:
    BASEDIR = "C:/your_main_folder"  # any empty folder on your system
    JWT = "your_JWT_key"  # get your JWT from https://jwt.comma.ai/
    if BASEDIR == "C:/your_main_folder" or JWT == "your_JWT_key":
        raise Exception('Please fill in the BASEDIR and JWT variables at the top of this file.')


os.chdir(BASEDIR)


class CommaVideoDownloader:
    def __init__(self):
        """
            This tool allows multiple simultaneous downloads, simply keep pasting route names and hit enter.
            Copying and pasting directly from your browser is supported, so if Chrome replaces | with %7C, it will still work.
            For example: 'e010b634f3d65cdb%7C2020-02-26--07-03-49'
            To get a list of drives, go to https://my.comma.ai/useradmin and click on your dongle id.
                The ids under `route_name` is what you want to paste here.
        """

        self.new_data_folder = 'new_data'
        self.downloaded_dir = '{}/downloaded'.format(self.new_data_folder)
        self.video_extension = '.hevc'
        self.route_threads = []
        self.setup_dirs()
        self.api_url = 'https://api.commadotai.com/v1/route/{}/files'
        self.download_loop()

    def download_loop(self):
        while True:
            print('Paste route name (ex. 23c2ed1a31ce0bda|2020-02-28--05-41-41)')
            route_name = input('>> ')
            Thread(target=self.start_downloader, args=(route_name,)).start()
            time.sleep(2)

    def start_downloader(self, route_name):
        if route_name not in self.route_threads:
            self.route_threads.append(route_name)
        else:
            print('Thread already downloading route!')
            return

        response = requests.get(self.api_url.format(route_name), headers={'Authorization': 'JWT {}'.format(JWT)})
        if response.status_code != 200:
            self.route_threads.remove(route_name)
            raise Exception('Returned status code: {}'.format(response.status_code))

        response = response.json()
        video_urls = response['cameras']
        route_folder = self.get_name_from_url(video_urls[0])[1]
        self.make_dirs('{}/{}'.format(self.downloaded_dir, route_folder))

        print('Starting download...', flush=True)

        for idx, video_url in enumerate(video_urls):
            print('Downloading video {} of {}...'.format(idx + 1, len(video_urls)), flush=True)
            video_name = self.get_name_from_url(video_url)[0]

            video_save_path = '{}/{}/{}'.format(self.downloaded_dir, route_folder, video_name)
            if os.path.exists(video_save_path):
                print('Error, video already downloaded: {}, skipping...'.format(video_name))
                continue

            video = requests.get(video_url)  # don't download until we check if video already exists

            with open(video_save_path, 'wb') as f:
                f.write(video.content)
            if idx + 1 == len(video_urls):
                print('Successfully downloaded {} videos!'.format(len(video_urls)))
                break
            else:
                time.sleep(1)
        else:
            print('No new videos on this route! Please try again or wait until they have uploaded from your EON/C2.')

        self.route_threads.remove(route_name)

    def get_name_from_url(self, video_url):
        video_name = video_url.split('_')[-1]
        video_name = video_name[:video_name.index(self.video_extension) + len(self.video_extension)]
        return video_name, '--'.join(video_name.split('--')[:2])

    def make_dirs(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    def setup_dirs(self):
        if not os.path.exists(self.downloaded_dir):
            os.makedirs(self.downloaded_dir)  # makes both folders recursively


video_downloader = CommaVideoDownloader()
