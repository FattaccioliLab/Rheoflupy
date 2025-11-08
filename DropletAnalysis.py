import numpy as np
import pandas as pd
import trackpy as tp
from scipy.signal import argrelmax

import matplotlib.pyplot as plt

def track_droplets(img_stack, stack_offset, diameter, minmass, search_range, track_out_fpath, filter_range=None, maxsize=None, 
                   link_memory=0, track_procs=4, df_savepath=None, clean_after=True):
    with tp.PandasHDFStore(track_out_fpath) as s:
        tp.batch(img_stack, diameter, minmass=minmass, processes=4, output=s)
        # As before, we require a minimum "life" of 5 frames and a memory of 3 frames
        for linked in tp.link_df_iter(s, search_range=search_range, memory=link_memory, link_strategy='auto'):
            s.put(linked)
        t = pd.concat(iter(s))
        
    if clean_after:
        os.remove(track_out_fpath)
    
    track_df = t.copy()
    track_df['y'] = t['y'] + stack_offset[1]
    track_df['x'] = t['x'] + stack_offset[2]
    track_df['frame'] = t['frame'] + stack_offset[0]
    
    if filter_range is not None:
        groups = track_df.groupby('particle')
        particles_in_range = []
        for name, group in groups:
            if group['x'].min() <= filter_range[0][0] and \
                group['x'].max() >= filter_range[0][1] and \
                group['y'].min() >= filter_range[1][0] and \
                group['y'].max() <= filter_range[1][1]:
                particles_in_range.append(name)
        track_df = track_df[track_df['particle'].isin(particles_in_range)]
        print('Filtering trajectories reduced dataset from {0} to {1} particles'.format(len(t['particle'].unique()), len(track_df['particle'].unique())))
        
    if df_savepath is not None:
        track_df.to_csv(df_savepath)
    PID_list = track_df['particle'].unique()
    
    return track_df, PID_list

def calc_droplet_stress(x_px, px_size, fps, eta, verbose=0, params=None):
    x_pos = np.array(px_size * x_px)
    v = np.gradient(x_pos, 1./fps) #um/s
    dvdx = np.gradient(v, x_pos)
    stress = eta*dvdx

    if verbose>1:
        maxidx = argrelmax(v)[0]
        if len(maxidx)>1:
            period = (maxidx[1]-maxidx[0])/fps
        else:
            print('WARNING: unable to estimate period from flow speed')
            period = np.nan
        omega = 2*np.pi/period
        vmax = np.max(v)
        print('Maximum droplet speed:  vmax = {0:.1f} µm/s'.format(vmax))
        print('Frequency:             omega = {0:.1f} rad/s'.format(omega))
        if params is not None:
            q_est = params['L0']*vmax*1e-6
            print('Planar flow rate (est.):   q = {0:.2f} mm2/s'.format(q_est*1e6))
            print('Reduced frequency (exp)  w/q = {0:.3f} 1/mm2'.format(omega/(q_est*1e6)))
            print('Reduced frequency (params)   = {0:.3f} 1/mm2'.format(params['omega']/(params['q']*1e6)))
            print('Real stress amplitude: sigma = {0:.1f} Pa'.format(params['stress_amp']/params['omega']*omega))
            print('Stress amplitude (params): s = {0:.1f} Pa'.format(params['stress_amp']))
    
    return x_pos*1e-6, v*1e-6, stress

def track_postproc(track_df, px_size, fps, eta, save_fname=None, plot=True, verbose=0, x_off=0, params=None):
    if plot:
        fig, ax = plt.subplots()
        ax2 = ax.twinx()
    if save_fname is not None:
        res_data = []
        str_hdr = ''        
    PID_list = track_df['particle'].unique()
    for cur_PID in PID_list:
        x_pos, v, stress = calc_droplet_stress(track_df[(track_df['particle'] == cur_PID)]['x'], px_size=px_size, fps=fps, eta=eta, verbose=verbose, params=params)
        x_pos *= 1e6
        v *= 1e6
        if plot:
            ax.plot(x_pos-x_off, v*1e-3, ls=':')
            ax2.plot(x_pos-x_off, stress)
        if save_fname is not None:
            res_data.append(x_pos-x_off)
            res_data.append(v*1e-3)
            res_data.append(stress)
            if str_hdr != '':
                str_hdr += '\t'
            str_hdr += 'x_{0}[um]\tv_{0}[mm/s]\ts_{0}[Pa]'.format(cur_PID)
    if plot:
        ax.set_ylabel(r'$v$ [mm/s]')
        ax.set_xlabel(r'$x-x_0$ [µm]')
        ax2.set_ylabel(r'$\sigma$ [Pa]')
        if params is not None:
            ax.set_xlim([0, params['wavelength_um']*1e6])
    if save_fname is not None:
        max_len = np.max([len(x) for x in res_data])
        for i in range(len(res_data)):
            for j in range(max_len-len(res_data[i])):
                res_data[i] = np.append(res_data[i], np.nan)
        np.savetxt(os.path.join(froot, img_name+'_stress.dat'), np.array(res_data).T, delimiter='\t', header=str_hdr)