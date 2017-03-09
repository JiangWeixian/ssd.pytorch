import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
from data import c9_2, pool6
from math import sqrt as sqrt
from itertools import product as product
if torch.cuda.is_available():
    torch.set_default_tensor_type('torch.cuda.FloatTensor')


class PriorBox(object):
    def __init__(self, cfg, clip=False):
        super(PriorBox, self).__init__()
        # self.type = cfg.name
        self.image_size = cfg['min_dim']
        self.num_priors = len(cfg['aspect_ratios']) # number of priors for feature map location (either 4 or 6)
        self.variance = cfg['variance'] or [0.1]
        self.feature_maps = cfg['feature_maps']
        self.min_sizes = cfg['min_sizes']
        self.max_sizes = cfg['max_sizes']
        self.steps = cfg['steps']
        self.aspect_ratios = cfg['aspect_ratios']
        self.clip = cfg['clip']
        self.version = cfg['name']
        for v in self.variance:
            if v <= 0:
                raise ValueError('Variances must be greater than 0')


    def forward(self):
        mean = []
        # TODO merge these
        if self.version == 'pool6':
            for i,k in enumerate(self.feature_maps):
                for h, w in product(range(k), repeat=2):
                    cx = (w + 0.5) * self.steps[i]
                    cy = (h + 0.5) * self.steps[i]
                    # aspect_ratio: 1
                    # size: min_size
                    s_k = self.min_sizes[i]/self.image_size
                    mean += [cx, cy, s_k, s_k]
                    if(self.max_sizes[i] > 0):
                        # aspect_ratio: 1
                        # size: sqrt(min_size * max_size)
                        s_k = sqrt(self.min_sizes[i] * self.max_sizes[i])
                        mean += [cx, cy, s_k, s_k]
                    s_k = self.min_sizes[i]/self.image_size
                    # rest of prior boxes
                    for ar in self.aspect_ratios[i]:
                        if abs(ar-1) < 1e-6:
                            continue
                        mean += [cx, cy, s_k/sqrt(ar), s_k*sqrt(ar)]
                        mean += [cx, cy, s_k*sqrt(ar), s_k/sqrt(ar)]


        else:
            # original version generation of prior (default) boxes
            for i,k in enumerate(self.feature_maps):
                step_x = step_y = self.image_size/k
                for h, w in product(range(k), repeat=2):
                   c_x = ((w+0.5) * step_x)
                   c_y = ((h+0.5) * step_y)
                   c_w = c_h = self.min_sizes[i] / 2
                   s_k = self.image_size
                   # aspect_ratio: 1,
                   # size: min_size
                   mean += [(c_x-c_w)/s_k, (c_y-c_h)/s_k, (c_x+c_w)/s_k, (c_y+c_h)/s_k]
                   if self.max_sizes[i] > 0:
                       # aspect_ratio: 1
                       # size: sqrt(min_size * max_size)/2
                       c_w = c_h = sqrt(self.min_sizes[i] * self.max_sizes[i])/2
                       mean += [(c_x-c_w)/s_k, (c_y-c_h)/s_k, (c_x+c_w)/s_k, (c_y+c_h)/s_k]
                   # rest of prior boxes
                   for ar in self.aspect_ratios[i]:
                       if not (abs(ar-1) < 1e-6):
                           c_w = self.min_sizes[i] *sqrt(ar)/2
                           c_h = self.min_sizes[i] /sqrt(ar)/2
                           mean += [(c_x-c_w)/s_k, (c_y-c_h)/s_k, (c_x+c_w)/s_k, (c_y+c_h)/s_k]
        # back to torch land
        output = torch.Tensor(mean).view(-1,4)
        if self.clip:
            output.clamp_(max=1, min=0)
        return output