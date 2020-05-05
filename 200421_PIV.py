import sys
import os
import numpy as np
import configparser
import warnings
import time
import openpiv
from openpiv import windef
from pims import ImageSequence
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

if os.name == 'nt':
    path_sep = '\\'
else:
    path_sep = '/'


ProgramRoot = os.path.dirname(sys.argv[0]) + path_sep
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
    
    out_froot = SharedFunctions.ConfigGet(config, 'output', 'output_folder') + path_sep
    time_prefix = SharedFunctions.ConfigGet(config, 'output', 'time_prefix', '', str)
    lag_prefix = SharedFunctions.ConfigGet(config, 'output', 'lag_prefix', '', str)
    img_ext = SharedFunctions.ConfigGet(config, 'input', 'image_ext', '', str)
    settings = ReadPIVsettings(config)
    froot = settings.filepath_images
    lagtimes = SharedFunctions.ConfigGet(config, 'input', 'lagtimes', None, int)
    zrange = SharedFunctions.ConfigGet(config, 'input', 'zrange', None, int)
    zidx_len = SharedFunctions.ConfigGet(config, 'input', 'zidx_len', 4, int)
    zprefix = SharedFunctions.ConfigGet(config, 'input', 'zprefix', 'Z', str)
    aggr_subfolder = SharedFunctions.ConfigGet(config, 'output', 'aggregated_subfolder', 'Aggregated', str)
    aggr_root = out_froot + aggr_subfolder + path_sep
    vel_prefix = SharedFunctions.ConfigGet(config, 'postprocess', 'vel_prefix', '_v', str)
    refinedv_prefix = SharedFunctions.ConfigGet(config, 'postprocess', 'refinedv_prefix', '__v', str)
    plots_subfolder = SharedFunctions.ConfigGet(config, 'output', 'plots_subfolder', None, str)
    if (plots_subfolder is None):
        plot_root = None
    else:
        plot_root = out_froot + plots_subfolder + path_sep
        
    
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
            print('Processing {0} image couples: {1}*{2}*{4} - {1}*{3}*{4}'.format(len(imgs_list), froot, settings.frame_pattern_a,\
                                                                                  settings.frame_pattern_b, img_ext))
        else:
            if (zrange is None):
                z_list = ['']
            else:
                z_list = []
                if (len(zrange)<3):
                    zrange.append(1)
                for zidx in range(zrange[0], zrange[1], zrange[2]):
                    z_list.append(zprefix+str(zidx).zfill(zidx_len))
            for z_suffix in z_list:
                fnamelist = SharedFunctions.FindFileNames(froot, Ext=z_suffix+img_ext, FilterString=settings.frame_pattern_a, AppendFolder=False)
                for i in range(len(fnamelist)):
                    for dt in lagtimes:
                        if (i+dt < len(fnamelist)):
                            imgs_list.append({'imgA':fnamelist[i],'imgB':fnamelist[i+dt],'t':i,'dt':dt, 'z_suf':z_suffix})

            print('{0} image couples to be processed: {1} images in {2}*{3}*{4}, {5} lagtimes {6}'.format(len(imgs_list),\
                  len(fnamelist), froot, settings.frame_pattern_a, z_suffix+img_ext, len(lagtimes), lagtimes))
        
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
                cur_outfolder = out_froot + time_prefix + str(imgs_list[i]['t']).zfill(4) + path_sep
                SharedFunctions.CheckCreateFolder(cur_outfolder)
                settings.save_path = cur_outfolder
                settings.save_folder_suffix = lag_prefix + str(imgs_list[i]['dt']).zfill(4)
                if (imgs_list[i]['z_suf'] != ''):
                    settings.save_folder_suffix = settings.save_folder_suffix + imgs_list[i]['z_suf']
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

    elif (SharedFunctions.CheckFolderExists(out_froot) == False):
        
        print('\nNo results to aggregate! Skipping aggregation step')

    else:

        print('\nNow aggregating output results...')
        
        dirlist = SharedFunctions.FindSubfolders(out_froot, FirstLevelOnly=True, Prefix=time_prefix)
        print('{0} "{1}{2}*{3}" subfolders found'.format(len(dirlist), out_froot, time_prefix, path_sep))
        
        laglist = SharedFunctions.ExtractIndexFromStrings(SharedFunctions.FindSubfolders(dirlist[0], FirstLevelOnly=True,\
                                     Prefix='Open_PIV_results_', FilterString=lag_prefix), index_pos=-1, index_notfound=-1)
        print('{0} times found, {1} lags found in first folder'.format(len(dirlist), len(laglist)))
        
        if (SharedFunctions.CheckFolderExists(aggr_root)):
            if (SharedFunctions.query_yes_no('Folder {0} already present. Rename it?'.format(aggr_root), default="yes")):
                sub_idx = 1
                while SharedFunctions.CheckFolderExists(out_froot + 'Aggregated_' + str(sub_idx) + path_sep):
                    sub_idx += 1
                aggr_root_renamed = out_froot + 'Aggregated_' + str(sub_idx) + path_sep
                SharedFunctions.RenameDirectory(out_froot + aggr_subfolder, out_froot + 'Aggregated_' + str(sub_idx))
                print('Folder originally named {0} renamed to {0}'.format(aggr_root, aggr_root_renamed))
            else:
                print('Results will be overwritten')                
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
                    if (SharedFunctions.CheckFileExists(subdirlist[lidx]+path_sep+'field_A000.txt')):
                        piv_data = np.loadtxt(subdirlist[lidx]+path_sep+'field_A000.txt', dtype=float, comments='#', usecols=(2,3,4,5))
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

    if ('-skippostproc' in cmd_list):

        print('\nSkipping post processing')
    
    else:
        
        print('\nNow postprocessing results to extract velocities...')
        
        vel_method = SharedFunctions.ConfigGet(config, 'postprocess', 'vel_method', 'linreg', str)
        save_vsq = SharedFunctions.ConfigGet(config, 'postprocess', 'save_vsq', False, bool)
        if (vel_method == 'none'):
            
            raise ValueError('Postprocessing method ' + vel_method + ' not implemented yet')
            
        if (vel_method == 'linreg'):
            max_lag_list = SharedFunctions.ConfigGet(config, 'postprocess', 'max_lag', -1, int)
            
            res_filenames = [SharedFunctions.FindFileNames(aggr_root, Prefix='dx_'+lag_prefix, Ext='.raw'),\
                            SharedFunctions.FindFileNames(aggr_root, Prefix='dy_'+lag_prefix, Ext='.raw'),\
                            SharedFunctions.FindFileNames(aggr_root, Prefix='mask_'+lag_prefix, Ext='.raw'),\
                            SharedFunctions.FindFileNames(aggr_root, Prefix='sn_'+lag_prefix, Ext='.raw')]
            imgInfo = [BinaryImgs.MIinfoFromName(res_filenames[0][0], byteFormat='f'),\
                       BinaryImgs.MIinfoFromName(res_filenames[1][0], byteFormat='f'),\
                       BinaryImgs.MIinfoFromName(res_filenames[2][0], byteFormat='B'),\
                       BinaryImgs.MIinfoFromName(res_filenames[3][0], byteFormat='f')]
            for cur_info in imgInfo:
                cur_info['hdr_size'] = 0
            
            res_files = []
            for fidx in range(len(res_filenames)):
                res_files.append([])
                for lidx in range(len(laglist)):
                    res_files[fidx].append(BinaryImgs.LoadMIfile(aggr_root + res_filenames[fidx][lidx], MI_info=imgInfo[fidx].copy(), returnHeader=False))
            
            laglist = SharedFunctions.ExtractIndexFromStrings(res_filenames[0], index_pos=0, index_notfound=0)
            
            fout_list = []
            lag_selidx_list = []
            lag_selval_list = []
            max_laglen_idx = 0
            for midx in range(len(max_lag_list)):
                
                strext = '_' + '_' + lag_prefix + str(max_lag_list[midx]) + '_' + str(imgInfo[0]['img_width']).zfill(4) +\
                                   'x' + str(imgInfo[0]['img_height']).zfill(4) + 'x' + str(imgInfo[0]['img_num']).zfill(4) + '.raw'
                
                do_add = True
                if (SharedFunctions.CheckFileExists(aggr_root + vel_prefix + 'x' + strext) and SharedFunctions.CheckFileExists(aggr_root + vel_prefix + 'y' + strext)):
                    overwrite_existing = SharedFunctions.ConfigGet(config, 'postprocess', 'overwrite_existing', 'ask', str)
                    if (overwrite_existing == 'no'):
                        do_add = False
                    elif (overwrite_existing == 'ask' and not SharedFunctions.query_yes_no('  For lagtime #{0} ({1}), output files are already in folder {2}. Overwrite them?', default="no")):
                        do_add = False
                
                if (do_add):
                    lag_selidx_list.append([])
                    lag_selval_list.append([])
                    for lidx in range(len(laglist)):
                        if (max_lag_list[midx] < 0 or laglist[lidx] <= max_lag_list[midx]):
                            lag_selidx_list[midx].append(lidx)
                            lag_selval_list[midx].append(laglist[lidx])
                    if (len(lag_selidx_list[midx]) > len(lag_selidx_list[max_laglen_idx])):
                        max_laglen_idx = midx
                    fout_list.append([BinaryImgs.OpenMIfileForWriting(aggr_root + vel_prefix + 'x' + strext),\
                                      BinaryImgs.OpenMIfileForWriting(aggr_root + vel_prefix + 'y' + strext)])
                    if (save_vsq):
                        fout_list[-1].append(BinaryImgs.OpenMIfileForWriting(aggr_root + vel_prefix + 'sq' + strext))
            
            time_start = time.time()
            for tidx in range(imgInfo[0]['img_num']):
                time_step = time.time()
                curt_mask = np.zeros((len(lag_selidx_list[max_laglen_idx]), imgInfo[2]['px_num']), dtype=bool)
                curt_dx = np.zeros((len(lag_selidx_list[max_laglen_idx]), imgInfo[2]['px_num']), dtype=float)
                curt_dy = np.zeros((len(lag_selidx_list[max_laglen_idx]), imgInfo[2]['px_num']), dtype=float)
                curt_lags = np.zeros((len(lag_selidx_list[max_laglen_idx]), imgInfo[2]['px_num']), dtype=float)
                for lidx in range(len(lag_selidx_list[max_laglen_idx])):
                    # mask==1: invalid vector
                    curt_mask[lidx] = BinaryImgs.getSingleImage_MIfile(res_files[2][lag_selidx_list[max_laglen_idx][lidx]], imgInfo[2], tidx, flatten_image=True)
                    curt_dx[lidx] = BinaryImgs.getSingleImage_MIfile(res_files[0][lag_selidx_list[max_laglen_idx][lidx]], imgInfo[0], tidx, flatten_image=True)
                    curt_dy[lidx] = BinaryImgs.getSingleImage_MIfile(res_files[1][lag_selidx_list[max_laglen_idx][lidx]], imgInfo[1], tidx, flatten_image=True)
                for midx in range(len(lag_selidx_list)):
                    if (fout_list[midx] is not None):
                        slopes = np.ones((imgInfo[2]['px_num'], 2), dtype=float) * np.nan
                        for pidx in range(imgInfo[2]['px_num']):
                            slopes[pidx,0] = SharedFunctions.LinearFit(lag_selval_list[midx], curt_dx[lag_selidx_list[midx],pidx], return_residuals=False, mask=curt_mask[:,pidx], catchex=False, nonan=True)
                            slopes[pidx,1] = SharedFunctions.LinearFit(lag_selval_list[midx], curt_dy[lag_selidx_list[midx],pidx], return_residuals=False, mask=curt_mask[:,pidx], catchex=False, nonan=True)
                        BinaryImgs.AppendToMIfile(fout_list[midx][0], slopes[:,0], 'f')
                        BinaryImgs.AppendToMIfile(fout_list[midx][1], slopes[:,1], 'f')
                        if (save_vsq):
                            BinaryImgs.AppendToMIfile(fout_list[midx][2], np.add(np.square(slopes[:,0]),np.square(slopes[:,1])), 'f')
                time_end = time.time()
                print('[{0}/{1}] Data for time {2} processed in {3:.1f} s. Elapsed time: {4:.1f} s'.format(tidx+1, imgInfo[0]['img_num'],\
                                                                          tidx, time_end-time_step, time_end-time_start))
            
            for midx in range(len(lag_selidx_list)):
                if (fout_list[midx] is not None):
                    for fidx in range(len(fout_list[midx])):
                        fout_list[midx][fidx].close()
            for fidx in range(len(res_files)):
                for lidx in range(len(res_files[fidx])):
                    res_files[fidx][lidx].close()
            
        else:
            
            raise ValueError('Postprocessing method ' + vel_method + ' not recognized')

        vel_filenames = [SharedFunctions.FindFileNames(aggr_root, Prefix=vel_prefix+'x', FilterString=vel_method, Ext='.raw'),\
                         SharedFunctions.FindFileNames(aggr_root, Prefix=vel_prefix+'y', FilterString=vel_method, Ext='.raw')]
        # TODO: go through velocity by lagtimes, starting from high, and figure out what's the best lagtime to use
    
    if ('-skipplot' in cmd_list or plot_root is None):
        
        print('Skipping plot step')
        
    else:
        
        SharedFunctions.CheckCreateFolder(plot_root)
        refinedv_filenames = [SharedFunctions.FindFileNames(aggr_root, Prefix=refinedv_prefix+'x', Ext='.raw'),\
                              SharedFunctions.FindFileNames(aggr_root, Prefix=refinedv_prefix+'y', Ext='.raw')]
    
        if (len(refinedv_filenames[0]) <= 0):
            raise ValueError('No ' + str(refinedv_prefix+'x') + '*.raw file in folder ' + str(aggr_root))
        if (len(refinedv_filenames[1]) <= 0):
            raise ValueError('No ' + str(refinedv_prefix+'y') + '*.raw file in folder ' + str(aggr_root))
        
        imgInfo = BinaryImgs.MIinfoFromName(refinedv_filenames[0][0], byteFormat='f')
        imgInfo['hdr_size'] = 0
        refinedv_data = BinaryImgs.ReadMIfileList([aggr_root+refinedv_filenames[0][0],aggr_root+refinedv_filenames[1][0]], MI_info=imgInfo, asArray=True)
        
        imSeq = ImageSequence(froot+SharedFunctions.ConfigGet(config, 'input', 'filter_frameA', '', str)+'*'+img_ext)
        piv_coords = openpiv.process.get_coordinates(image_size=imSeq[0].shape, window_size=settings.windowsizes[settings.iterations-1],\
                                        overlap=settings.overlap[settings.iterations-1])
        bin_xy = 4
        bin_z = 4
        piv_coords_binned = [SharedFunctions.downsample2d(piv_coords[0], bin_xy),\
                             SharedFunctions.downsample2d(piv_coords[1], bin_xy)]
        num_times = len(refinedv_data[0]) // bin_z
        refinedv_data_binned = [SharedFunctions.downsample3d(refinedv_data[0][:num_times*bin_z], bin_xy, bin_z),\
                                SharedFunctions.downsample3d(refinedv_data[1][:num_times*bin_z], bin_xy, bin_z)]
        imSeq_binned = SharedFunctions.downsample3d(imSeq[:num_times*bin_z], 1, bin_z)
        refinedv_data_binz = [SharedFunctions.downsample3d(refinedv_data[0][:num_times*bin_z], 1, bin_z),\
                                SharedFunctions.downsample3d(refinedv_data[1][:num_times*bin_z], 1, bin_z)]
        diverg3D = np.add(np.gradient(refinedv_data_binz[0])[2], np.gradient(refinedv_data_binz[1])[1])
        maxalpha = np.power(np.nanmax(np.absolute(diverg3D[:-3])), 0.3)
        cmap_bounds = [0, np.nanmax(diverg3D[:-3])]
        for tidx in range(min(len(imSeq), len(refinedv_data_binned[0]))):
            fig, ax = plt.subplots(figsize=(10,10))
            ax.imshow(imSeq_binned[tidx], extent=[0, 1024, 0, 1024], origin='upper', vmin=30, vmax=80, cmap='Greys_r')
            ax.quiver(piv_coords_binned[0], piv_coords_binned[1], refinedv_data_binned[0][tidx], -refinedv_data_binned[1][tidx], color='blue', linewidth=2,\
                      scale=1)
            x_str, y_str = np.unique(piv_coords[0].flatten())[::bin_xy], np.unique(piv_coords[1].flatten())[::bin_xy]
            #ax.streamplot(x_str, y_str, refinedv_data_binned[0][tidx], -refinedv_data_binned[1][tidx],\
            #              density=[1,0.6], linewidth=1.0, color='r', cmap='hot', arrowsize=1.0, minlength=0.04)
            
            diverg = diverg3D[tidx]
            my_cmap = plt.cm.get_cmap('hot')
            alphas = Normalize(vmin=0.6*maxalpha, vmax=0.9*maxalpha, clip=True)(np.power(np.absolute(np.nan_to_num(diverg)), 0.3))   # Create an alpha channel based on weight values. Any value whose absolute value is > .0001 will have zero transparency
            alphas = np.clip(alphas, 0.0, 0.95)  # alpha value clipped at the bottom at .4
            print(np.max(alphas))
            colors = Normalize(vmin=cmap_bounds[0], vmax=cmap_bounds[1])(diverg) # Normalize the colors b/w 0 and 1, we'll then pass an MxNx4 array to imshow
            colors = my_cmap(colors)
            colors[..., -1] = alphas   # Now set the alpha channel to the one we created above
            #cur_imshow_kw = {'extent' : [PIV_avg['x'][0]*0.5, PIV_avg['x'][-1]+PIV_avg['x'][0]*0.5,\
            #                               PIV_avg['y'][-1]+PIV_avg['y'][0]*0.5, PIV_avg['y'][0]*0.5],}
            #if False:
            #    cur_imshow_kw['vmin'] = _config['OUT']['overlay_vbounds'][0]
            #    cur_imshow_kw['vmax'] = _config['OUT']['overlay_vbounds'][1]
            ax.imshow(colors, extent=[0, 1024, 0, 1024], origin='upper')#, **cur_imshow_kw)
            ax.set_position([0, 0, 1, 1])
            plt.axis('off')
            #plt.tight_layout()
            fig.savefig(plot_root + str(tidx).zfill(4) + '.png')
            plt.close('all')