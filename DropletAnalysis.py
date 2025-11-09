import os
import time
import shutil
import numpy as np
import pandas as pd
import trackpy as tp
from scipy.signal import argrelmax
from scipy.optimize import curve_fit, least_squares
from sklearn.cluster import DBSCAN
from subpixel_edges import subpixel_edges

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

import IOfunctions as iof

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
        
def find_edges(image, edge_threshold, smoothing_iterN, dbscan_eps=1, dbscan_minN=1, plot=False):
    drop_edges = subpixel_edges(image, edge_threshold, smoothing_iterN, 2)
    edge_points = np.array([drop_edges.x,drop_edges.y]).T
    out_edge, cluster_labels = extract_outer_edge(edge_points, dbscan_eps, dbscan_minN)
    if plot:
        plt.figure()
        plt.scatter(edge_points[:, 0], edge_points[:, 1], c=cluster_labels, cmap='Paired', alpha=0.5)
        plt.scatter(out_edge[:, 0], out_edge[:, 1], c='red', label='Selected edge points')
        plt.legend()
    return out_edge

def extract_outer_edge(edge_points, eps, min_samples):
    # DBSCAN clustering
    db = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
    y_pred = db.fit_predict(edge_points)
    unique_labels = set(y_pred)
    unique_labels.discard(-1)

    centroids, average_radii, cluster_data = [], [], []

    # Calculate centroids, average radii, and sizes for each cluster
    for label in unique_labels:
        points = edge_points[y_pred == label]
        cluster_size = len(points)
        centroid = np.mean(points, axis=0)
        centroids.append(centroid)

        radii = np.linalg.norm(points - centroid, axis=1)
        average_radius = np.mean(radii)
        average_radii.append(average_radius)

        if cluster_size > 0:
            xc=np.mean(np.array(points[:,0]))
            yc=np.mean(np.array(points[:,1]))
        cluster_data.append([label, cluster_size, np.array([xc, yc])])

    # Sort clusters by size and take the top two largest clusters
    top_two_clusters = sorted(cluster_data, key=lambda x: x[1], reverse=True)[:2]

    tot_n = np.sum([x[1] for x in top_two_clusters])
    true_center = [x[2]*(x[1]/tot_n) for x in top_two_clusters]
    true_center = np.sum(true_center, axis=0)

    #add radius to the cluster data
    for i in range(len(top_two_clusters)):
        num_points = len(edge_points[y_pred == top_two_clusters[i][0]])
        top_two_clusters[i].append((np.linalg.norm(np.array(edge_points[y_pred == top_two_clusters[i][0]]) - true_center))/num_points)
    top_two_clusters.sort(key=lambda x: x[3], reverse=True)

    if len(top_two_clusters) < 1: 
        print("Less than one clusters found.")
        return None, None
    else:
        # Among the top two clusters, select the one with the smallest average radius
        outermost_label = top_two_clusters[0][0]
        # Extract the points that belong to the innermost circle
        outermost_points = edge_points[y_pred == outermost_label]
        return outermost_points, y_pred

def poly_fit_theta(theta, c1, c2, c3, c4, c5):
    return 1 + c1*np.cos(theta) + c2*np.cos(2*theta) + c3*np.cos(3*theta) + c4*np.cos(4*theta) + c5*np.cos(5*theta)

def fit_edge(drop_edges, filter_r_thr=100, logfile=None, frame_n=None, plot=True, plot_savedir=None): # the edges are before rotation

    raw_x, raw_y = drop_edges[:,0], drop_edges[:,1]
    
    #filter out r and theta value where r greater than r_bar, only fit inner circle
    raw_r = np.sqrt((raw_x - np.mean(raw_x))**2 + (raw_y - np.mean(raw_y))**2)
    filt_idx = np.where(raw_r <= np.mean(raw_r) + filter_r_thr)
    x = raw_x[filt_idx]
    y = raw_y[filt_idx]

    # renew centers
    cx, cy = np.mean(x), np.mean(y)
    xcorr, ycorr = x - cx, y - cy
    r, theta = np.sqrt(xcorr**2 + ycorr**2), np.arctan2(ycorr, xcorr)

    # calculate r_bar, which is the mean radius
    r_bar = np.mean(r)
    r_norm = r / r_bar    
    if logfile is not None:
        with open(os.path.join(dir, 'output.txt'), 'a') as file:
            file.write(f'Frame {frame_n}: r_bar = {r_bar}\n')

    popt, pcov = curve_fit(poly_fit_theta, theta, r_norm, p0=[0,0.1,0,0,0])
    # now popt contains the Fourier coefficients of the droplet deformation
        
    if plot:
        # Plot the reconstructed droplet shape
        theta_fit = np.linspace(-np.pi, np.pi, 1000)
        r_fit = r_bar * poly_fit_theta(theta_fit, *popt)
        r_ellipse = r_bar * poly_fit_theta(theta_fit, popt[0], popt[1], 0, 0, 0)
        non_ellip = np.sum(np.abs(popt[2:]))/np.abs(popt[1])
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot(raw_x - np.mean(raw_x), raw_y - np.mean(raw_y), 'k.', label='Data')
        ax.plot(r_bar * np.cos(theta_fit), r_bar * np.sin(theta_fit), 'b:', label=r'Circle ($\bar r=$' + '{0:.1f}px)'.format(r_bar))
        ax.plot(r_ellipse * np.cos(theta_fit), r_ellipse * np.sin(theta_fit), 'g-', label=r'Ellipse ($\gamma_2=$' + '{0:.1f}%)'.format(popt[1]*100))
        ax.plot(r_fit * np.cos(theta_fit), r_fit * np.sin(theta_fit), 'r--', lw=2, label=r'Fit ($\Sigma\gamma_{n>2}/\gamma_2=$' + '{0:.2f})'.format(non_ellip))
        ax.set_aspect('equal')
        ax.yaxis.set_major_locator(ax.xaxis.get_major_locator())
        ax.legend()
        ax.grid(True)
        if plot_savedir is not None:
            fig.savefig(os.path.join(plot_savedir, f'fit_{frame_n}.png'))

    return popt, [cx, cy], r_bar

def analyze_deformations(img_path, track_df, crop_roi_size, img_bkg=None, img_bkgcorr_offset=0, img_blur_sigma=0, 
                         edge_threshold=5.5, smoothing_iterN=4, dbscan_eps=1, dbscan_minN=1, filter_r_thr=100, 
                         plot_outdir=None, px_size=1, fps=1):
    
    # Final lists to store results for successfully processed particles
    res_list, PID_sel = [], []
    PID_list = track_df['particle'].unique()
    
    for newcol in ['rbar', 'gamma1', 'gamma2', 'gamma3', 'gamma4', 'gamma5', 'xfit', 'yfit', 'vx', 'dvdx']:
        track_df[newcol] = np.nan

    count_skipped = 0
    t0 = time.time()
    for pID in PID_list:
        print('Now processing particle {0}/{1} (PID: {2})...'.format(len(PID_sel)+count_skipped+1, len(PID_list), pID))
        
        # Flag to track if the particle processing fails at any point
        particle_failed = False

        # Temporary lists for the current particle's data
        cur_res = np.empty((len(track_df[track_df['particle'] == pID]), 5), dtype=float)

        # Create directories for saving plots
        if plot_outdir is not None:
            cur_outdir = os.path.join(plot_outdir, str(pID))
            os.makedirs(cur_outdir, exist_ok=True)

        count = 0
        prev_x, prev_vx = np.nan, np.nan
        for framenum in track_df[track_df['particle'] == pID]['frame']:
            
            cur_record = track_df[(track_df['particle'] == pID) & (track_df['frame'] == framenum)]
            xloc, yloc = int(cur_record['x'].iloc[0]), int(cur_record['y'].iloc[0])
            
            # Extract Region of Interest (ROI) and process image
            drop_ROI = [xloc-crop_roi_size, yloc-crop_roi_size, xloc+crop_roi_size, yloc+crop_roi_size]
            drop_img = iof.get_single_frame(img_path, framenum, cropROI=drop_ROI, bkg=img_bkg, bkgcorr_offset=img_bkgcorr_offset, 
                                            blur_sigma=img_blur_sigma, dtype=float)
            drop_edges = find_edges(drop_img, edge_threshold=edge_threshold, smoothing_iterN=smoothing_iterN, 
                                    dbscan_eps=dbscan_eps, dbscan_minN=dbscan_minN, plot=False)
            
            # If circle extraction fails for any frame, mark the whole particle as failed
            if drop_edges is None:
                print(f"Clustering analysis failed on frame {framenum}. Skipping entire particle {pID}.")
                particle_failed = True
                break  # Exit the inner loop (over frames) immediately
            if drop_edges.shape[0] < 6:
                print(f"Analysis failed on frame {framenum}: too few edge datapoints to fit. Skipping entire particle {pID}.")
                particle_failed = True
                break  # Exit the inner loop (over frames) immediately

            # Continue with calculations if frame analysis was successful
            popt, ctrpos, rbar = fit_edge(drop_edges, filter_r_thr=filter_r_thr, logfile=None, frame_n=framenum, plot=True, plot_savedir=cur_outdir)
            cur_res[count] = (rbar, *popt[1:])

            # Update particle coordinates in the original DataFrame
            track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'xfit'] = xloc + ctrpos[0] - crop_roi_size 
            track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'yfit'] = yloc + ctrpos[1] - crop_roi_size
            track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'rbar'] = rbar
            track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'gamma1'] = popt[0]
            track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'gamma2'] = popt[1]
            track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'gamma3'] = popt[2]
            track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'gamma4'] = popt[3]
            track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'gamma5'] = popt[4]
            if count > 0:
                cur_v = (xloc - prev_x) * px_size * fps
                track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'vx'] = cur_v
                if count > 1:
                    track_df.loc[(track_df['particle'] == pID) & (track_df['frame'] == framenum), 'dvdx'] = (cur_v - prev_v) / ((xloc - prev_x) * px_size)
                prev_v = cur_v
            
            prev_x = xloc
            count += 1
            plt.close('all')

        # After processing all frames, check if the particle failed.
        # If it did, skip to the next particle without saving its results.
        if particle_failed:
            count_skipped += 1
            # Optional: Clean up the directory created for the failed particle
            try:
                shutil.rmtree(cur_outdir)
                print(f"Removed directory for failed particle {pID}.")
            except OSError as e:
                print(f"Error removing directory {cur_outdir}: {e.strerror}")
            continue # Skip to the next particle
        else:
            # If the particle was processed successfully, append its results to the final lists
            res_list.append(cur_res)
            PID_sel.append(pID)
            
    print('Analysis completed in {0:.1f} seconds. {1} particles successfully analyzed, {2} skipped'.format(time.time()-t0, len(PID_sel), count_skipped))

    return res_list, PID_sel