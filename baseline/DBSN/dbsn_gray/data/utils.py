import sys
import random
import time
import datetime
import numpy as np
import scipy.io as sio

from PIL import Image
from torch.utils.data import Dataset
import torchvision.transforms as transforms
import torchvision.transforms.functional as tvF
import h5py
import random
import torch
from torch.autograd import Variable

import math
from skimage import measure
from sklearn.metrics import mean_squared_error
from sklearn.feature_extraction import image

class TrdataLoader():

    def __init__(self, _tr_data_dir=None, _args = None):

        self.tr_data_dir = _tr_data_dir
        self.args = _args
        
        self.data = h5py.File(self.tr_data_dir, "r")

        self.noisy_arr = self.data["noisy_images"]
        self.clean_arr = self.data["clean_images"]
        self.num_data = self.clean_arr.shape[0]
            
        print ('num of training patches : ', self.num_data)

    def __len__(self):
        return self.num_data
    
    def __getitem__(self, index):
        
        # random crop
        

        if self.args.noise_type == 'Gaussian' or self.args.noise_type == 'Poisson-Gaussian':

            clean_img = self.clean_arr[index,:,:]
            noisy_img = self.noisy_arr[index,:,:]
            
            if self.args.data_type == 'Grayscale':
                
                rand = random.randrange(1,10000)
                
                clean_patch = image.extract_patches_2d(image = clean_img ,patch_size = (self.args.patch_size, self.args.patch_size), 
                                             max_patches = 1, random_state = rand)
                noisy_patch = image.extract_patches_2d(image = noisy_img ,patch_size = (self.args.patch_size, self.args.patch_size), 
                                             max_patches = 1, random_state = rand)
                
                            # Random horizontal flipping
                if random.random() > 0.5:
                    clean_patch = np.fliplr(clean_patch)
                    noisy_patch = np.fliplr(noisy_patch)

                # Random vertical flipping
                if random.random() > 0.5:
                    clean_patch = np.flipud(clean_patch)
                    noisy_patch = np.flipud(noisy_patch)
                    
            else:
                
                rand_x = random.randrange(0, (clean_img.shape[0] - self.args.patch_size -1) // 2)
                rand_y = random.randrange(0, (clean_img.shape[1] - self.args.patch_size -1) // 2)
                
                clean_patch = clean_img[rand_x*2 : rand_x*2 + self.args.patch_size, rand_y*2 : rand_y*2 + self.args.patch_size].reshape(1, self.args.patch_size, self.args.patch_size)
                noisy_patch = noisy_img[rand_x*2 : rand_x*2 + self.args.patch_size, rand_y*2 : rand_y*2 + self.args.patch_size].reshape(1, self.args.patch_size, self.args.patch_size)

            source = torch.from_numpy(noisy_patch.copy())
            target = torch.from_numpy(clean_patch.copy())

            return source, target
            
class TedataLoader():

    def __init__(self,_tedata_dir=None, args = None):

        self.te_data_dir = _tedata_dir
        
        self.data = h5py.File(self.te_data_dir, "r")
        self.clean_arr = self.data["clean_images"]
        self.noisy_arr = self.data["noisy_images"]
        self.num_data = self.noisy_arr.shape[0]
        self.args = args
        
        print ('num of test images : ', self.num_data)
        
    def __len__(self):
        return self.num_data
    
    def __getitem__(self, index):
        """Retrieves image from folder and corrupts it."""

        source = self.data["noisy_images"][index,:,:]
        target = self.data["clean_images"][index,:,:]

        source = torch.from_numpy(source.reshape(1,source.shape[0],source.shape[1])).cuda()
        target = torch.from_numpy(target.reshape(1,target.shape[0],target.shape[1])).cuda()
        

        return source, target
    
def get_PSNR(X, X_hat):

    mse = np.mean((X-X_hat)**2)
    test_PSNR = 10 * math.log10(1/mse)
    
    return test_PSNR

def get_SSIM(X, X_hat):

    test_SSIM = measure.compare_ssim(np.transpose(X, (1,2,0)), np.transpose(X_hat, (1,2,0)), data_range=X.max() - X.min(), multichannel=True)

    return test_SSIM






