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
import BinaryImgs
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
    
    cmd_list = []
    
    inp_fnames = [ProgramRoot + 'PIVdef.ini']
    for argidx in range(1, len(sys.argv)):
        # If it's something like -cmd, add it to the command list
        # Otherwise, assume it's the path of some input file to be read
        if (sys.argv[argidx][0] == '-'):
            cmd_list.append(sys.argv[argidx])
        else:
            inp_fnames.append(sys.argv[argidx])

    # Read input file for configuration
    config = configparser.ConfigParser(allow_no_value=True)
    for conf_f in inp_fnames:
        print('Reading config file: ' + str(conf_f))
        config.read(conf_f)
    
    out_froot = SharedFunctions.ConfigGet(config, 'output', 'output_folder') + '\\'
    time_prefix = SharedFunctions.ConfigGet(config, 'output', 'time_prefix', '', str)
    lag_prefix = SharedFunctions.ConfigGet(config, 'output', 'lag_prefix', '', str)
    img_ext = SharedFunctions.ConfigGet(config, 'input', 'image_ext', '', str)
    settings = ReadPIVsettings(config)
    froot = settings.filepath_images
    lagtimes = SharedFunctions.ConfigGet(config, 'input', 'lagtimes', None, int)
    
    # If -aggregate is in the command list,
    # only aggregate results, don't go through the PIV computation
    if ('-skipPIV' in cmd_list):
        
        print('\nSkipping PIV step.')
    
    else:
        
        imgs_list = []
        if (lagtimes is None and settings.frame_pattern_b == ''):
            lagtimes = [1]
        if (lagtimes is None):
            fnamelist_A = SharedFunctions.FindFileNames(froot, Ext=img_ext, FilterString=settings.frame_pattern_a, AppendFolder=False)
            fnamelist_B = SharedFunctions.FindFileNames(froot, Ext=img_ext, FilterString=settings.frame_pattern_b, AppendFolder=False)
            for i in range(min(len(fnamelist_A), len(fnamelist_B))):
                imgs_list.append({'imgA':fnamelist_A[i],'imgB':fnamelist_B[i],'t':i,'dt':0})
        else:
            fnamelist = SharedFunctions.FindFileNames(froot, Ext=img_ext, FilterString=settings.frame_pattern_a, AppendFolder=False)
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
        
        time_start = time.time()
        for i in range(len(imgs_list)):
            if (str_method == 'standard'):
                settings.frame_pattern_a = imgs_list[i]['imgA']
                settings.frame_pattern_b = imgs_list[i]['imgB']
                cur_outfolder = out_froot + time_prefix + str(imgs_list[i]['t']).zfill(4) + '\\'
                SharedFunctions.CheckCreateFolder(cur_outfolder)
                settings.save_path = cur_outfolder
                settings.save_folder_suffix = lag_prefix + str(imgs_list[i]['dt']).zfill(4)
                settings.show_plot = False
                
                time_step = time.time()
                windef.piv(settings)
                time_end = time.time()
                print('[{0}/{1}] Img #{2}, lag {3} processed in {4:.1f} s. Total elapsed: {5:.1f} s'.format(i+1, len(imgs_list), imgs_list[i]['t'],\
                      imgs_list[i]['dt'], time_end-time_step, time_end-time_start))
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
                                                       min_window_size=16, overlap_ratio=0.0, coarse_factor=2, dt=1, validation_method='mean_velocity',\
                                                       trust_1st_iter=1, validation_iter=1, tolerance=0.7, nb_iter_max=3, sig2noise_method='peak2peak')
        time_end = time.time()
        print('\n\n-----------\nDONE! {0} image pairs processed in {1:.1f} s.'.format(len(imgs_list), time_end-time_start))
    
    if ('-skipaggregate' in cmd_list):
        
        print('\nSkipping result aggregation')

    else:

        print('\nNow aggregating output results...')
        
        dirlist = SharedFunctions.FindSubfolders(out_froot, FirstLevelOnly=True, Prefix=time_prefix)
        print('{0} "{1}{2}*\\" subfolders found'.format(len(dirlist), out_froot, time_prefix))
        
        laglist = SharedFunctions.ExtractIndexFromStrings(SharedFunctions.FindSubfolders(dirlist[0], FirstLevelOnly=True,\
                                     Prefix='Open_PIV_results_', FilterString=lag_prefix), index_pos=-1, index_notfound=-1)
        print('{0} times found, {1} lags found in first folder'.format(len(dirlist), len(laglist)))
        
        aggr_root = out_froot + 'Aggregated\\'
        SharedFunctions.CheckCreateFolder(aggr_root)
        
        # Find coordinates
        img_list = SharedFunctions.FindFileNames(settings.filepath_images, Ext=SharedFunctions.ConfigGet(config, 'input', 'image_ext', '', str),\
                                                      FilterString=settings.frame_pattern_a, AppendFolder=False)
        frame_test = openpiv.tools.imread(settings.filepath_images + img_list[0])
        coords = openpiv.process.get_coordinates(image_size=frame_test.shape, window_size=settings.windowsizes[settings.iterations-1],\
                                        overlap=settings.overlap[settings.iterations-1])
        print('Image shape: {0}. Window size: {1}. Overlap: {2}. PIV grid shape: {3}x{4}'.format(frame_test.shape, settings.windowsizes[settings.iterations-1],\
                                                                  settings.overlap[settings.iterations-1], len(coords[0]), len(coords[1])))
        
        # Binary files for aggregated data
        strext = '_' + str(len(coords[0])).zfill(4) + 'x' + str(len(coords[1])).zfill(4) + 'x' + str(len(dirlist)).zfill(4) + '.raw'
        displ_x = []
        displ_y = []
        mask = []
        signoise = []
        for lidx in range(len(laglist)):
            cur_suffix = lag_prefix + str(laglist[lidx]).zfill(4) + strext
            displ_x.append(BinaryImgs.OpenMIfileForWriting(aggr_root + 'dx_' + cur_suffix))
            displ_y.append(BinaryImgs.OpenMIfileForWriting(aggr_root + 'dy_' + cur_suffix))
            mask.append(BinaryImgs.OpenMIfileForWriting(aggr_root + 'mask_' + cur_suffix))
            signoise.append(BinaryImgs.OpenMIfileForWriting(aggr_root + 'sn_' + cur_suffix))
        
        time_start = time.time()
        for tidx in range(len(dirlist)):
            time_step = time.time()
            cur_t = SharedFunctions.LastIntInStr(dirlist[tidx])
            subdirlist = SharedFunctions.FindSubfolders(dirlist[tidx], FirstLevelOnly=True, Prefix='Open_PIV_results_',\
                                                        FilterString=SharedFunctions.ConfigGet(config, 'output', 'lag_prefix', '', str))
            for lidx in range(len(laglist)):
                piv_data = None
                if (lidx < len(subdirlist)):
                    if (SharedFunctions.CheckFileExists(subdirlist[lidx]+'\\field_A000.txt')):
                        piv_data = np.loadtxt(subdirlist[lidx]+'\\field_A000.txt', dtype=float, comments='#', usecols=(2,3,4,5))
                if (piv_data is None):
                    piv_data = np.ones((len(coords[0])*len(coords[1]), 4), dtype=float)*np.nan
                BinaryImgs.AppendToMIfile(displ_x[lidx], piv_data[:,0], 'f')
                BinaryImgs.AppendToMIfile(displ_y[lidx], piv_data[:,1], 'f')
                BinaryImgs.AppendToMIfile(signoise[lidx], piv_data[:,2], 'f')
                BinaryImgs.AppendToMIfile(mask[lidx], piv_data[:,3], 'B')
            
            time_end = time.time()
            print('[{0}/{1}] Data for time {2} aggregated in {3:.1f} s. Elapsed time: {4:.1f} s'.format(tidx+1, len(dirlist),\
                                                                          cur_t, time_end-time_step, time_end-time_start))
            
        for lidx in range(len(laglist)):
            displ_x[lidx].close()
            displ_y[lidx].close()
            mask[lidx].close()
            signoise[lidx].close()
            