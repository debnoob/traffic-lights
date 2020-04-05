from keras.backend.tensorflow_backend import set_session
import tensorflow as tf
import os
import cv2
import random
from utils.basedir import BASEDIR
import string
from threading import Thread
from threading import Lock
import matplotlib.pyplot as plt
import time
import keras
import numpy as np
import shutil

os.chdir(BASEDIR)

config = tf.ConfigProto()
config.gpu_options.per_process_gpu_memory_fraction = 0.8
set_session(tf.Session(config=config))


class EasyClassifier:  # todo: implement smart skip. low skip value when model predicts traffic light, high skip when model predicts none
    def __init__(self):
        self.data_labels = ['RED', 'GREEN', 'YELLOW', 'NONE']
        self.model_labels = ['SLOW', 'GREEN', 'NONE']
        self.data_dir = 'data'
        self.to_add_dir = '{}/to_add'.format(self.data_dir)
        self.extracted_dir = 'new_data/extracted'
        self.already_classified_dir = 'new_data/extracted/already_classified'
        self.routes = [i for i in os.listdir(self.extracted_dir) if i not in ['already_classified', 'todo', 'temp']]
        self.frame_rate = 20
        self.default_skip = int(0.5 * self.frame_rate)  # amount of frames to skip

        self.skip = 0
        self.user_skip = 0

        self.model_name = 'latest_3_class_93_val_acc'
        self.model = keras.models.load_model('models/h5_models/{}.h5'.format(self.model_name))
        self.graph = tf.get_default_graph()

        self.max_preloaded_routes = 2  # number of routes to preload
        self.preloaded_routes = []
        self.all_routes_done = False
        self.lock = Lock()

        self.make_dirs()

    def start(self):
        Thread(target=self.route_preloader).start()
        self.classifier_manager()

    def classifier_manager(self):
        print('-----\n  Valid inputs:')
        print('  {class} - Move image to class folder')
        print('  skip {num frames} - Set the number of frames to skip')
        print('  skip {num frames} now - Skip n frames now\n-----')
        while True:
            if len(self.preloaded_routes) > 0:
                print('NEXT ROUTE!')
                this_route = self.preloaded_routes[0]
                with self.lock:
                    del self.preloaded_routes[0]
                self.start_classifying(this_route)
            elif self.all_routes_done and len(self.preloaded_routes) == 0:
                print('All routes classified!')
                return
            else:
                time.sleep(1)

    def route_preloader(self):
        for route in self.routes:
            while len(self.preloaded_routes) >= self.max_preloaded_routes:
                time.sleep(1)  # too many preloaded, wait until user is done with preloaded routes

            route_dir = '{}/{}'.format(self.extracted_dir, route)
            list_dir = self.sort_list_dir(os.listdir(route_dir))  # sorted using integar values of frame idx
            print('Route: {}'.format(route))
            print('Loading all images from route to predict, please wait...', flush=True)
            all_imgs = self.load_imgs_from_directory(list_dir, route_dir)
            if len(all_imgs) > 0:
                print('Loaded all images! Now predicting...', flush=True)
                with self.lock:
                    self.preloaded_routes.append({'route_predictions': self.predict_multiple(all_imgs),
                                                  'route_name': route,
                                                  'route_dir': route_dir,
                                                  'list_dir': list_dir,
                                                  'all_imgs': all_imgs})
            else:
                print('Skipping bad folder...')
                self.move_folder(route_dir, self.already_classified_dir)
            del all_imgs  # free unused memory

        self.all_routes_done = True

    def start_classifying(self, route):
        print('Route: {}'.format(route['route_name']))
        route_predictions = route['route_predictions']
        for idx, (img, img_name) in enumerate(zip(route['all_imgs'], route['list_dir'])):
            if self.skip != 0 and self.user_skip == 0:  # this skips ahead in time
                self.skip -= 1
                continue
            else:
                self.skip = int(self.default_skip)

            if self.user_skip != 0:
                self.user_skip -= 1
                continue
            print('At frame: {}'.format(idx))

            plt.clf()
            plt.imshow(self.crop_image(self.BGR2RGB(img), False))

            pred = route_predictions[idx]
            pred_idx = np.argmax(pred)

            plt.title('Prediction: {} ({}%)'.format(self.model_labels[pred_idx], round(pred[pred_idx] * 100, 2)))
            plt.pause(0.01)

            output_dict = self.get_true_label(self.data_labels[pred_idx])
            if output_dict['skip']:
                continue
            else:
                correct_label = output_dict['label']
                img_path = '{}/{}'.format(route['route_dir'], img_name)
                self.move(img_path, '{}/{}/{}'.format(self.to_add_dir, correct_label, img_name))

        self.reset_skip()
        self.move_folder(route['route_dir'], self.already_classified_dir)

    def sort_list_dir(self, list_dir):  # because the way os and sorted() sorts the files is incorrect but technically correct
        file_nums = [int(file.split('.')[-2]) for file in list_dir]
        return [fi_num for _, fi_num in sorted(zip(file_nums, list_dir))]

    def load_imgs_from_directory(self, list_dir, route_dir):
        imgs = []
        for img_name in list_dir:
            img_path = '{}/{}'.format(route_dir, img_name)
            img = cv2.imread(img_path)
            if img is None:  # skips bad files
                continue
            imgs.append(np.array((img / 255.0), dtype=np.float32))
        return imgs

    def get_true_label(self, model_pred):
        labels = {'R': 'RED', 'G': 'GREEN', 'N': 'NONE', 'Y': 'YELLOW'}

        while True:
            u_input = input('> ').strip(' ').upper()
            if u_input in labels:
                print('Moved to {} folder!'.format(labels[u_input]))
                return {'label': labels[u_input], 'correct': False, 'skip': False}
            elif u_input in labels.values():
                print('Moved to {} folder!'.format(u_input))
                return {'label': u_input, 'correct': False, 'skip': False}
            elif 'SKIP' in u_input:
                u_input = u_input.split(' ')
                try:
                    skip_parsed = float(u_input[1])
                    if len(u_input) == 3:  # if followed by 'now', skip now
                        if u_input[-1] == 'NOW':
                            self.user_skip = max(int(skip_parsed * self.frame_rate), 0)
                            self.skip = 0
                            print('Skipping {} frames!'.format(self.user_skip))
                            return {'label': None, 'correct': None, 'skip': True}
                    elif len(u_input) == 2:  # else set default skip
                        self.default_skip = max(int(skip_parsed * self.frame_rate), 0)
                        self.skip = int(self.default_skip)
                        self.user_skip = 0
                        print('Set skipping to {} frames!'.format(self.default_skip))
                        continue
                except:
                    print('Exception when parsing input to skip, try again!')
                    continue
            print('Invalid input, try again!')

    def move_folder(self, source, destination):
        shutil.move(source, destination)

    def move(self, source, destination):
        os.rename(source, destination)

    def reset_skip(self):
        self.skip = 0
        self.user_skip = 0

    def predict_multiple(self, imgs):
        imgs_cropped = [self.crop_image(img, False) for img in imgs]
        with self.graph.as_default():  # workaround for using tf model in thread
            predictions = self.model.predict(np.array(imgs_cropped))
        return predictions

    def crop_image(self, img_array, crop_top):
        h_crop = 175  # horizontal, 150 is good, need to test higher vals
        if crop_top:
            t_crop = 150  # top, 100 is good. test higher vals
        else:
            t_crop = 0
        y_hood_crop = 665
        return img_array[t_crop:y_hood_crop, h_crop:-h_crop]  # removes 150 pixels from each side, removes hood, and removes 100 pixels from top

    def BGR2RGB(self, arr):
        return cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)

    def make_dirs(self):
        try:
            for lbl in self.data_labels:
                os.makedirs('{}/{}'.format(self.to_add_dir, lbl))
        except:
            pass
        try:
            os.makedirs(self.already_classified_dir)
        except:
            pass


easy_classifier = EasyClassifier()
easy_classifier.start()
