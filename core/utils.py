import glob
import os.path
import sys
import random
import time
import datetime
import numpy as np
import scipy.io as sio

from PIL import Image
from torch.fx.experimental.unification.multipledispatch.dispatcher import source
from torch.utils.data import Dataset
import torchvision.transforms as transforms
import torchvision.transforms.functional as tvF
import h5py
import random
import torch
from torch.autograd import Variable

import math
#from skimage import measure
from skimage.metrics import structural_similarity as compare_ssim
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
                
                clean_patch = image.extract_patches_2d(image = clean_img ,patch_size = (self.args.crop_size, self.args.crop_size), 
                                             max_patches = 1, random_state = rand)
                noisy_patch = image.extract_patches_2d(image = noisy_img ,patch_size = (self.args.crop_size, self.args.crop_size), 
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

                rand_x = random.randrange(0, (clean_img.shape[0] - self.args.crop_size -1) // 2)
                rand_y = random.randrange(0, (clean_img.shape[1] - self.args.crop_size -1) // 2)

                clean_patch = clean_img[rand_x*2 : rand_x*2 + self.args.crop_size, rand_y*2 : rand_y*2 + self.args.crop_size].reshape(1, self.args.crop_size, self.args.crop_size)
                noisy_patch = noisy_img[rand_x*2 : rand_x*2 + self.args.crop_size, rand_y*2 : rand_y*2 + self.args.crop_size].reshape(1, self.args.crop_size, self.args.crop_size)

            
            if self.args.loss_function == 'MSE':
            
                source = torch.from_numpy(noisy_patch.copy())
                target = torch.from_numpy(clean_patch.copy())
                
                return source, target
            
            elif self.args.loss_function == 'MSE_Affine' or self.args.loss_function == 'N2V' or self.args.loss_function == 'Noise_est' or self.args.loss_function == 'EMSE_Affine':
                
                source = torch.from_numpy(noisy_patch.copy())
                target = torch.from_numpy(clean_patch.copy())
                
                target = torch.cat([source,target], dim = 0)
                
                return source, target

        else: ## real data
               
            return source, target
    
class TedataLoader():

    def __init__(self,_te_data_dir=None, args = None):

        self.te_raw_data_dir = glob.glob(os.path.join(_te_data_dir,'raw/*.png'),recursive=True)
        self.te_gt_data_dir = glob.glob(os.path.join(_te_data_dir,'gt/*.png'),recursive=True)
        #if 'SIDD' in self.te_data_dir or 'DND' in self.te_data_dir or 'CF' in self.te_data_dir or 'TP' in self.te_data_dir:
        self.te_raw_data_dir.sort()
        self.te_gt_data_dir.sort()
        #else:
            #self.data = h5py.File(self.te_data_dir, "r")

        self.num_data = len(self.te_raw_data_dir)
        self.args = args
        
        print ('num of test images : ', self.num_data)
        
    def __len__(self):
        return self.num_data
    
    def __getitem__(self, index):
        """Retrieves image from folder and corrupts it."""
        raw_img_path = self.te_raw_data_dir[index]
        gt_img_path = self.te_gt_data_dir[0]
        raw_img = Image.open(raw_img_path)
        gt_img = Image.open(gt_img_path)
        source = np.array(raw_img,dtype=np.float32)
        target = np.array(gt_img,dtype=np.float32)

        
        #if 'SIDD' in self.te_data_dir or 'CF' in self.te_data_dir or 'TP' in self.te_data_dir:
        source = source / 255.
        target = target / 255.

        source = torch.from_numpy(source.reshape(1,source.shape[0],source.shape[1])).float().cuda()
        target = torch.from_numpy(target.reshape(1,target.shape[0],target.shape[1])).float().cuda()
        
        if self.args.loss_function == 'MSE_Affine' or self.args.loss_function == 'N2V':
            target = torch.cat([source,target], dim = 0)
        print('data loading successful---------------------------')
        return source, target
    
def get_PSNR(X, X_hat):

    mse = np.mean((X-X_hat)**2)
    test_PSNR = 10 * math.log10(1/mse)
    
    return test_PSNR

def get_SSIM(X, X_hat):

    test_SSIM = compare_ssim(np.transpose(X, (1,2,0)), np.transpose(X_hat, (1,2,0)),channel_axis=2, data_range=X.max() - X.min(), multichannel=True)

    return test_SSIM



def im2patch(im,pch_size,stride=1):
    if isinstance(pch_size, tuple):
        pch_H, pch_W = pch_size
    elif isinstance(pch_size, int):
        pch_H = pch_W = pch_size
    else:
        sys.exit('The input of pch_size must be a integer or a int tuple!')
    if isinstance(stride, tuple):
        stride_H, stride_W = stride
    elif isinstance(stride, int):
        stride_H = stride_W = stride
    else:
        sys.exit('The input of stride must be a integer or a int tuple!')

    C, H, W = im.size()
    num_H = len(range(0, H-pch_H+1, stride_H))
    num_W = len(range(0, W-pch_W+1, stride_W))
    num_pch = num_H * num_W
    pch = torch.zeros((C, pch_H*pch_W, num_pch)).cuda()
    kk = 0
    for ii in range(pch_H):
        for jj in range(pch_W):
            temp = im[:, ii:H-pch_H+ii+1:stride_H, jj:W-pch_W+jj+1:stride_W]
            pch[:, kk, :] = temp.reshape((C, num_pch))
            kk += 1

    return pch.view((C, pch_H, pch_W, num_pch))

def chen_estimate(im,pch_size=8):
    im=torch.squeeze(im)
    
    #grayscale
    im=im.unsqueeze(0)
    pch=im2patch(im,pch_size,3)
    num_pch=pch.size()[3]
    pch=pch.view((-1,num_pch))
    d=pch.size()[0]
    mu=torch.mean(pch,dim=1,keepdim=True)
    
    X=pch-mu
    sigma_X=torch.matmul(X,torch.t(X))/num_pch
    sig_value,_=torch.symeig(sigma_X,eigenvectors=True)
    sig_value=sig_value.sort().values
    
    
    start=time.time()
    # tensor operation for substituting iterative step.
    # These operation make  parallel computing possiblie which is more efficient

    triangle=torch.ones((d,d))
    triangle= torch.tril(triangle).cuda()
    sig_matrix= torch.matmul( triangle, torch.diag(sig_value)) 
    
    # calculate whole threshold value at a single time
    num_vec= torch.arange(d)+1
    num_vec=num_vec.to(dtype=torch.float32).cuda()
    sum_arr= torch.sum(sig_matrix,dim=1)
    tau_arr=sum_arr/num_vec
    
    tau_mat= torch.matmul(torch.diag(tau_arr),triangle)
    
    # find median value with masking scheme: 
    big_bool= torch.sum(sig_matrix>tau_mat,axis=1)
    small_bool= torch.sum(sig_matrix<tau_mat,axis=1)
    mask=(big_bool==small_bool).to(dtype=torch.float32).cuda()
    tau_chen=torch.max(mask*tau_arr)
      
# Previous implementation       
#    for ii in range(-1, -d-1, -1):
#        tau = torch.mean(sig_value[:ii])
#        if torch.sum(sig_value[:ii]>tau) == torch.sum(sig_value[:ii] < tau):
             #  return torch.sqrt(tau)
#    print('old: ', torch.sqrt(tau))

    return torch.sqrt(tau_chen)

def gat(z,sigma,alpha,g):
    _alpha=torch.ones_like(z)*alpha
    _sigma=torch.ones_like(z)*sigma
    z=z/_alpha
    _sigma=_sigma/_alpha
    f=(2.0)*torch.sqrt(torch.max(z+(3.0/8.0)+_sigma**2,torch.zeros_like(z)))
    return f

def inverse_gat(z,sigma1,alpha,g,method='asym'):
   # with torch.no_grad():
    sigma=sigma1/alpha
    if method=='closed_form':
        exact_inverse = ( np.power(z/2.0, 2.0) +
              0.25* np.sqrt(1.5)*np.power(z, -1.0) -
              11.0/8.0 * np.power(z, -2.0) +
              5.0/8.0 * np.sqrt(1.5) * np.power(z, -3.0) -
              1.0/8.0 - sigma**2 )
        exact_inverse=np.maximum(0.0,exact_inverse)
    elif method=='asym':
        exact_inverse=(z/2.0)**2-1.0/8.0-sigma
    else:
        raise NotImplementedError('Only supports the closed-form')
    if alpha !=1:
        exact_inverse*=alpha
    if g!=0:
        exact_inverse+=g
    return exact_inverse
# def inverse_gat_torch(z,sigma1,alpha,g,method='asym'):
#  #   with torch.no_grad():
#     sigma=sigma1/alpha
#     if method == 'closed_form':
#         exact_inverse = (torch.pow(z/2.0, 2.0) + 0.25* torch.rsqrt(torch.tensor(1.5))*torch.pow(z, -1.0) - 11.0/8.0 * torch.pow(z, -2.0) + 5.0/8.0 * torch.rsqrt(torch.tensor(1.5)) * torch.pow(z, -3.0) -  1.0/8.0 - sigma**2 ).cuda()
#         exact_inverse=torch.max(torch.tensor(0.0).cuda(),exact_inverse)
#     elif method == 'asym':
#         exact_inverse=(z/2.0)**2-1.0/8.0-sigma
#     else:
#         raise NotImplementedError('Only supports the closed-form')
#     if alpha !=1:
#         exact_inverse*=alpha
#     if g!=0:
#         exact_inverse+=g
#     return exact_inverse

def normalize_after_gat_torch(transformed):
    min_transform=torch.min(transformed)
    max_transform=torch.max(transformed)

    transformed=(transformed-min_transform)/(max_transform-min_transform)
    transformed_sigma= 1/(max_transform-min_transform)
    transformed_sigma=torch.ones_like(transformed)*(transformed_sigma)
    return transformed, transformed_sigma, min_transform, max_transform

