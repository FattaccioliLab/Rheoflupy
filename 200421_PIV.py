import sys
import os
import numpy as np
import configparser
import warnings
import time
import openpiv
from openpiv import windef
#import matplotlib.pyplot as plt

ProgramRoot = os.path.dirname(sys.argv[0]) + '\\'
sys.path.append(ProgramRoot)
#import BinaryImgs
import SharedFunctions


def ReadPIVsettings(config):
    settings = windef.Settings()
    settings.filepath_images             = SharedFunctions.ConfigGet(config, 'input',      'input_folder')
    settings.frame_pattern_a             = SharedFunctions.ConfigGet(config, 'input',      'filter_frameA', '', str)
    settings.frame_pattern_b             = SharedFunctions.ConfigGet(config, 'input',      'filter_frameB', '', str)
    settings.ROI                         = SharedFunctions.ConfigGet(config, 'input',      'ROI')
    settings.dynamic_masking_method      = 'None'
    settings.dynamic_masking_threshold   = 0.005
    settings.dynamic_masking_filter_size = 7
    settings.correlation_method          = SharedFunctions.ConfigGet(config, 'processing', 'correlation_method')
    settings.iterations                  = SharedFunctions.ConfigGet(config, 'processing', 'iterations', 1, int)
    settings.windowsizes                 = SharedFunctions.ConfigGet(config, 'processing', 'window_sizes', [4], int)
    settings.overlap                     = SharedFunctions.ConfigGet(config, 'processing', 'overlap', [2], int)
    settings.subpixel_method             = SharedFunctions.ConfigGet(config, 'processing', 'subpixel_method')
    settings.interpolation_order         = SharedFunctions.ConfigGet(config, 'processing', 'interpolation_order', 3, int)
    settings.scaling_factor              = SharedFunctions.ConfigGet(config, 'processing', 'pixel_size', 1.0, float)
    settings.dt                          = SharedFunctions.ConfigGet(config, 'processing', 'dt', 1.0, float)
    settings.extract_sig2noise           = SharedFunctions.ConfigGet(config, 'processing', 'extract_sig2noise', False, bool)
    settings.sig2noise_method            = SharedFunctions.ConfigGet(config, 'processing', 'sig2noise_method')
    settings.sig2noise_mask              = SharedFunctions.ConfigGet(config, 'processing', 'sig2noise_mask', 2, int)
    settings.validation_first_pass       = SharedFunctions.ConfigGet(config, 'validation', 'validation_first_pass', False, bool)
    settings.MinMax_U_disp               = SharedFunctions.ConfigGet(config, 'validation', 'MinMax_U_disp', [-1000.0, 1000.0], float)
    settings.MinMax_V_disp               = SharedFunctions.ConfigGet(config, 'validation', 'MinMax_V_disp', [-1000.0, 1000.0], float)
    settings.std_threshold               = SharedFunctions.ConfigGet(config, 'validation', 'std_threshold', 7.0, float)
    settings.median_threshold            = SharedFunctions.ConfigGet(config, 'validation', 'median_threshold', 3.0, float)
    settings.median_size                 = SharedFunctions.ConfigGet(config, 'validation', 'median_size', 1, int)
    settings.do_sig2noise_validation     = SharedFunctions.ConfigGet(config, 'validation', 'do_sig2noise_validation', False, bool)
    settings.sig2noise_threshold         = SharedFunctions.ConfigGet(config, 'validation', 'sig2noise_threshold', 1.2, float)
    settings.replace_vectors             = SharedFunctions.ConfigGet(config, 'validation', 'replace_vectors', True, bool)
    settings.smoothn                     = SharedFunctions.ConfigGet(config, 'validation', 'smoothn', True, bool)
    settings.smoothn_p                   = SharedFunctions.ConfigGet(config, 'validation', 'smoothn_p', 0.5, float)
    settings.filter_method               = SharedFunctions.ConfigGet(config, 'validation', 'filter_method')
    settings.max_filter_iteration        = SharedFunctions.ConfigGet(config, 'validation', 'max_filter_iteration', 4, int)
    settings.filter_kernel_size          = SharedFunctions.ConfigGet(config, 'validation', 'filter_kernel_size', 2.0, float)
    settings.save_path                   = SharedFunctions.ConfigGet(config, 'output',     'output_folder')
    settings.save_folder_suffix          = SharedFunctions.ConfigGet(config, 'output',     'save_folder_suffix')
    settings.save_plot                   = SharedFunctions.ConfigGet(config, 'output',     'save_plot', False, bool)
    settings.show_plot                   = SharedFunctions.ConfigGet(config, 'output',     'show_plot', False, bool)
    settings.scale_plot                  = SharedFunctions.ConfigGet(config, 'output',     'scale_plot', 1.0, float)
    return settings






if __name__ == '__main__':
    
    inp_fnames = [ProgramRoot + 'PIVdef.ini']
    if (len(sys.argv) > 1):
        inp_fnames.append(sys.argv[1])

    # Read input file for configuration
    config = configparser.ConfigParser(allow_no_value=True)
    for conf_f in inp_fnames:
        print('Reading config file: ' + str(conf_f))
        config.read(conf_f)

    settings = ReadPIVsettings(config)
    froot = settings.filepath_images
    lagtimes = SharedFunctions.ConfigGet(config, 'input', 'lagtimes', None, int)
    
    imgs_list = []
    if (lagtimes is None and settings.frame_pattern_b == ''):
        lagtimes = [1]
    if (lagtimes is None):
        fnamelist_A = SharedFunctions.FindFileNames(froot, Ext=SharedFunctions.ConfigGet(config, 'input', 'image_ext', '', str),\
                                                    FilterString=settings.frame_pattern_a, AppendFolder=False)
        fnamelist_B = SharedFunctions.FindFileNames(froot, Ext=SharedFunctions.ConfigGet(config, 'input', 'image_ext', '', str),\
                                                    FilterString=settings.frame_pattern_b, AppendFolder=False)
        for i in range(min(len(fnamelist_A), len(fnamelist_B))):
            imgs_list.append({'imgA':fnamelist_A[i],'imgB':fnamelist_B[i],'t':i,'dt':0})
    else:
        fnamelist = SharedFunctions.FindFileNames(froot, Ext=SharedFunctions.ConfigGet(config, 'input', 'image_ext', '', str),\
                                                  FilterString=settings.frame_pattern_a, AppendFolder=False)
        for i in range(len(fnamelist)):
            for dt in lagtimes:
                if (i+dt < len(fnamelist)):
                    imgs_list.append({'imgA':fnamelist[i],'imgB':fnamelist[i+dt],'t':i,'dt':dt})
    print('{0} image couples to be processed'.format(len(imgs_list)))
    
    str_method = SharedFunctions.ConfigGet(config, 'processing', 'PIV_method', 'standard', str)
    if (str_method == 'standard'):
        print('Using standard PIV method')
    elif (str_method == 'WiDIM'):
        raise ValueError('WiDIM method not implemented yet')
    elif (str_method == 'extended'):
        raise ValueError('extended_search_area method not implemented yet')
    else:
        raise ValueError('Method ' + str_method + ' not recognized')
    
    for i in range(len(imgs_list)):
        
        if (str_method == 'standard'):
            settings.frame_pattern_a = imgs_list[i]['imgA']
            settings.frame_pattern_b = imgs_list[i]['imgB']
            cur_outfolder = SharedFunctions.ConfigGet(config, 'output', 'output_folder') + '\\T' + str(imgs_list[i]['t']).zfill(4) + '\\'
            SharedFunctions.CheckCreateFolder(cur_outfolder)
            settings.save_path = cur_outfolder
            settings.save_folder_suffix = 'LAG' + str(imgs_list[i]['dt']).zfill(4)
            settings.show_plot = False
            
            time_start = time.time()
            windef.piv(settings)
            time_end = time.time()
            print('[{0}/{1}] Image #{2} - lagtime {3} processed in {4} s'.format(i, len(imgs_list), imgs_list[i]['t'], imgs_list[i]['dt'], time_start-time_end))
        elif (str_method == 'WiDIM'):
            # Warning: implementing this feature...
            cur_frameA = openpiv.tools.imread(froot+imgs_list[i]['imgA'])
            cur_frameB = openpiv.tools.imread(froot+imgs_list[i]['imgB'])
            if (settings.dynamic_masking_method != 'None'):
                raise ValueError('settings.dynamic_masking_method must be None for the moment, not ' + str(settings.dynamic_masking_method))
            mark = np.ones(cur_frameA.shape, dtype=np.int32)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                x,y,u,v,mask=openpiv.process.WiDIM(cur_frameA.astype(np.int32), cur_frameB.astype(np.int32), mark,\
                                                   min_window_size=16, overlap_ratio=0.0, coarse_factor=2, dt=1, validation_method='mean_velocity', trust_1st_iter=1, validation_iter=1, tolerance=0.7, nb_iter_max=3, sig2noise_method='peak2peak')
    #dir(windef)
    windef.piv(settings)