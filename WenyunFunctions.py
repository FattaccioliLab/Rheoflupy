import os
import cv2
import shutil # Import shutil for directory cleanup
import numpy as np

import skimage.io as io
from sklearn.cluster import DBSCAN
from scipy.optimize import curve_fit, least_squares

import matplotlib.pyplot as plt
from matplotlib_scalebar.scalebar import ScaleBar

from subpixel_edges import subpixel_edges


def poly_fit_theta(x, a,b,c,d,e):
    return 1 + a*np.cos(x)+b*np.cos(2*x) + c*np.cos(3*x) + d*np.cos(4*x) + e*np.cos(5*x)

def calculate_gamma_fit(y,x,dir,framenum, r_prime:int = 5., get_outer:bool = False): # the edges are before rotation
    """ Calculate the Fourier coefficients of the vesicle deformation
        :param y: y coordinates of the vesicle edge
        :param x: x coordinates of the vesicle edge
        :param dir: the directory to save the output
        :param framenum: the frame number
        :param r_prime: vesicle thickness
        :param get_outer: whether to get the outer layer of the vescile countour
        :return: the Fourier coefficients of the vesicle deformation """
    
    #edges_rotated=np.rot90(edges,k=-1)
    #indices=np.nonzero(edges)
    # calculate the centroid of the droplet
    centroid_x = np.mean(x)
    centroid_y = np.mean(y)

    # subtract the centroid from the x and y values to center the droplet at (0, 0)
    centered_x = x - centroid_x
    centered_y = y - centroid_y

    # now you can calculate r and theta from the centered x and y values
    r = np.sqrt(centered_x**2 + centered_y**2)

    # calculate r_bar, which is the mean radius
    r_thres = np.mean(r)
    #filter out r and theta value where r greater than r_bar, only fit inner circle
    filtered_indices = np.where(r <= r_thres+100)
    filtered_x=x[filtered_indices]
    filtered_y=y[filtered_indices]

    # renew centers
    filtered_centroid_x = np.mean(filtered_x)
    filtered_centroid_y = np.mean(filtered_y)

    filtered_centered_x = filtered_x - filtered_centroid_x
    filtered_centered_y = filtered_y - filtered_centroid_y

    filtered_r = np.sqrt(filtered_centered_x**2 + filtered_centered_y**2)
    filtered_theta = np.arctan2(filtered_centered_y, filtered_centered_x)

    # calculate r_bar, which is the mean radius
    r_bar = np.mean(filtered_r)
    # normalize r by r_bar
   
    r_normalized = filtered_r / r_bar
    
    with open(os.path.join(dir, 'output.txt'), 'a') as file:
        file.write(f'Frame {framenum}: r_bar = {r_bar}\n')

    p = [0.1,0.1,0.1,0.1,0.1]
    popt, pcov = curve_fit(poly_fit_theta, filtered_theta, r_normalized,p0=p)

    # now gamma contains the Fourier coefficients of the droplet deformation

    # Number of points we want for the reconstructed droplet
    N_points = 1000
    # Array of theta values for the reconstructed droplet
    theta_reconstructed = np.linspace(-np.pi, np.pi, N_points)
    # Start with the average radius for the reconstructed droplet
    r_reconstructed = poly_fit_theta(theta_reconstructed,*popt)* r_bar

    # Convert back to Cartesian coordinates for plotting
    x_reconstructed = r_reconstructed * np.cos(theta_reconstructed)
    y_reconstructed = r_reconstructed * np.sin(theta_reconstructed)

    plot_filename = os.path.join(dir, f'reconstructed_{framenum}.png')

    def scaling_gammaN(r_prime):
        scaling_factor = (r_bar + r_prime) / r_bar
        r_reconstructed_outer = poly_fit_theta(theta_reconstructed, *popt/scaling_factor) * (r_bar + r_prime)
        x_reconstructed_outer = r_reconstructed_outer * np.cos(theta_reconstructed)
        y_reconstructed_outer = r_reconstructed_outer * np.sin(theta_reconstructed)

        return popt/scaling_factor, r_bar+r_prime, x_reconstructed_outer, y_reconstructed_outer

    if get_outer:
        gammaN, r_outer, x_reconstructed_outer, y_reconstructed_outer = scaling_gammaN(r_prime)
        popt = gammaN
        r_bar = r_outer
        
    # Plot the reconstructed droplet shape
    if get_outer:
        plt.figure(figsize=(6, 6))
        plt.plot(centered_x, centered_y, '.')
        plt.plot(x_reconstructed, y_reconstructed)
        plt.plot(x_reconstructed_outer, y_reconstructed_outer)
        plt.axis('equal')
        plt.grid(True)
        plt.savefig(plot_filename)
    else:
        plt.figure(figsize=(6, 6))
        plt.plot(centered_x, centered_y, '.')
        plt.plot(x_reconstructed, y_reconstructed)
        plt.axis('equal')  # ensure the x and y axis scales are equal
        plt.grid(True)
        plt.savefig(plot_filename)  # Save the plot to a file

    return popt, filtered_centroid_x, filtered_centroid_y, r_bar
    
def sine_func(x, A, B, C, D):
    return A * np.sin(B * x + C) + D

def sine_func_freq(x, A, C, D, omega=0.1):  # Here, omega is given a default value of 1.0, but you can replace it with any other value
    return A * np.sin(omega * x + C) + D

# It's good practice to encapsulate repeated plotting logic in a helper function.
def _save_plot_with_scalebar(filename, image_data, pixel_size_um, scale_bar_length_pixels, edges=None):
    """Helper function to save an image with a scale bar and optional quiver plot."""
    plt.figure() # Create a new figure to avoid plotting on the same canvas
    plt.imshow(image_data, cmap='gray')
    if edges is not None:
        plt.quiver(edges.x, edges.y, edges.nx, -edges.ny, scale=60, color='r')
    
    # Calculate the length fraction for the scale bar relative to the image width
    length_fraction = scale_bar_length_pixels / image_data.shape[1]
    scalebar = ScaleBar(pixel_size_um, "µm", location='lower right', length_fraction=length_fraction)
    plt.gca().add_artist(scalebar)
    plt.axis('off') # Hide axes for a cleaner image
    plt.savefig(filename, bbox_inches='tight', pad_inches=0)
    plt.close()

# Note: The following helper functions are assumed to be defined elsewhere in your code:
# - subpixel_edges
# - extract_outermost_circle
# - _save_plot_with_scalebar
# - calculate_gamma_fit

def analyze_wavelength_helper(wavelength_data, wavenum, imgname, img_tif, dt, scale, ref, pixel_size_um, 
                              dbscan_esp=2.1, dbscan_min_samples=1, roi_size=75, diff=1.5, degree=4, 
                              save_plots=True):  # <-- MODIFICATION: Added save_plots flag
    
    # Calculate scale bar length in pixels
    scale_bar_length_um = 5  # Desired scale bar length in µm
    scale_bar_length_pixels = scale_bar_length_um / pixel_size_um
    
    size = roi_size
    unique_particles = wavelength_data['particle'].unique()
    
    # Final lists to store results for successfully processed particles
    gamma_2_list = []
    particle_num_list = []
    radius_list = []
    v_list = []

    # --- MAIN PARTICLE LOOP ---
    for particle in unique_particles[:50]:
        # Flag to track if the particle processing fails at any point
        particle_failed = False
        
        total_frames = wavelength_data[wavelength_data['particle'] == particle]['frame']

        # Temporary lists for the current particle's data
        gamma_2 = []
        single_particle_radius = []

        # Create directories for saving plots
        current_directory = os.getcwd()
        result_directory = os.path.join(current_directory, imgname, str(wavenum), str(particle))
        os.makedirs(result_directory, exist_ok=True)

        # --- FRAME-BY-FRAME ANALYSIS LOOP ---
        for framenum in total_frames:
            filtered_t1 = wavelength_data[(wavelength_data['particle'] == particle) & (wavelength_data['frame'] == framenum)]

            xloc = int(filtered_t1['x'].iloc[0])
            yloc = int(filtered_t1['y'].iloc[0])
            
            # Extract Region of Interest (ROI) and process image
            roi = img_tif[framenum][yloc-size:yloc+size, xloc-size:xloc+size]
            ref_roi = ref[yloc-size:yloc+size, xloc-size:xloc+size]
            parts = cv2.GaussianBlur(roi - ref_roi + 150, (5, 5), 2)
            
            img_gray = parts.astype(float)
            edges = subpixel_edges(img_gray, diff, degree, 2)
            edge_points = np.array([edges.x, edges.y]).T

            outermost_circle, _ = extract_outermost_circle(edge_points, dbscan_esp, dbscan_min_samples)

            # --- MODIFICATION START: Conditional Plotting ---
            # Only save plots if the flag is True
            if save_plots:
                plot_filename = os.path.join(result_directory, f'plot_{framenum}.png')
                _save_plot_with_scalebar(plot_filename, parts, pixel_size_um, scale_bar_length_pixels, edges=edges)

                parts_filename = os.path.join(result_directory, f'parts_{framenum}.png')
                _save_plot_with_scalebar(parts_filename, parts, pixel_size_um, scale_bar_length_pixels)
            # --- MODIFICATION END ---
            
            # If circle extraction fails for any frame, mark the whole particle as failed
            if outermost_circle is None:
                print(f"Analysis failed on frame {framenum}. Skipping entire particle {particle}.")
                particle_failed = True
                break  # Exit the inner loop (over frames) immediately

            # Continue with calculations if frame analysis was successful
            popt, xcenter, ycenter, rbar = calculate_gamma_fit(outermost_circle[:, 1], outermost_circle[:, 0], result_directory, framenum, get_outer=False)
            gamma_2.append(popt[1])
            single_particle_radius.append(rbar)

            # Update particle coordinates in the original DataFrame
            wavelength_data.loc[(wavelength_data['particle'] == particle) & (wavelength_data['frame'] == framenum), 'x'] = xloc - size + xcenter
            wavelength_data.loc[(wavelength_data['particle'] == particle) & (wavelength_data['frame'] == framenum), 'y'] = yloc - size + ycenter

        # After processing all frames, check if the particle failed.
        # If it did, skip to the next particle without saving its results.
        if particle_failed:
            # Optional: Clean up the directory created for the failed particle
            try:
                shutil.rmtree(result_directory)
                print(f"Removed directory for failed particle {particle}.")
            except OSError as e:
                print(f"Error removing directory {result_directory}: {e.strerror}")
            continue # Skip to the next particle

        # If the particle was processed successfully, append its results to the final lists
        gamma_2_list.append(gamma_2)
        particle_num_list.append(particle)
        radius_list.append(single_particle_radius)

        x_pos = wavelength_data[wavelength_data['particle'] == particle]['x']
        v = np.gradient(x_pos, dt) * scale
        v_list.append(v)

    return gamma_2_list, particle_num_list, radius_list, v_list



def calculate_modulus(framerate,gamma,sigma):
    lower_bounds = [0, 0,-0.1]
    upper_bounds = [np.inf, np.pi,0.1]

    if (type(gamma) is list) == True:
        x=np.arange(0,len(gamma))/framerate
        non_nan_indices = ~np.isnan(gamma)
        x=x[non_nan_indices]
        gamma=np.array(gamma)[non_nan_indices]
        fixed_omega=2 * np.pi / (len(gamma)/framerate)

        # Fit the sine function with the constraints
        params, _ = curve_fit(lambda x, A, B, C: sine_func_freq(x, A, B, C, omega=fixed_omega), x, gamma, p0=[0.05,2,0], method='trf', bounds=(lower_bounds, upper_bounds))
        print(fixed_omega)

        storage_modulus=sigma/params[0]*np.cos(np.pi-params[1])
        print('Storage modulus is:'+str(storage_modulus))
        loss_modulus=sigma/params[0]*np.sin(np.pi-params[1])
        print('Loss modulus is:'+str(loss_modulus))

		y_fit = sine_func_freq(x, *params,omega=fixed_omega)

		y=gamma
		residuals = y - y_fit
		ss_res = np.sum(residuals ** 2)
		ss_tot = np.sum((y - np.mean(y)) ** 2)
		r_squared = 1 - (ss_res / ss_tot)
		print('R^2: ' + str(r_squared))

		print(params)
		plt.plot(x, y, 'o', label='Data')
		plt.plot(x, y_fit, label='Fit')
		plt.show()
	else:
		storage_modulus=np.nan
		loss_modulus=np.nan
		fixed_omega=np.nan
		r_squared=np.nan
	return storage_modulus,loss_modulus, fixed_omega, r_squared

# def estimate_circle_center_and_radius(points):
#     def residuals(params, x, y):
#         xc, yc, r = params
#         return (x - xc)**2 + (y - yc)**2 - r**2

#     x = points[:, 0]
#     y = points[:, 1]
#     x_m = np.mean(x)
#     y_m = np.mean(y)

#     initial_guess = [x_m, y_m, np.mean(np.sqrt((x - x_m)**2 + (y - y_m)**2))]
#     result = least_squares(residuals, initial_guess, args=(x, y))
#     xc, yc, r_squared = result.x
#     return xc, yc, np.sqrt(r_squared)  # Return the center and the radius


def extract_innermost_circle(edge_points, eps, min_samples):
    # print("got here")
    # DBSCAN clustering
    db = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
    y_pred = db.fit_predict(edge_points)
    unique_labels = set(y_pred)
    unique_labels.discard(-1)

    centroids = []
    average_radii = []
    cluster_data = []

    # Calculate centroids, average radii, and sizes for each cluster
    for label in unique_labels:
        points = edge_points[y_pred == label]
        cluster_size = len(points)
        centroid = np.mean(points, axis=0)
        # print(centroid)
        centroids.append(centroid)

        radii = np.linalg.norm(points - centroid, axis=1)
        average_radius = np.mean(radii)
        average_radii.append(average_radius)

        if cluster_size > 0:
            #xc, yc, _ = estimate_circle_center_and_radius(points)
            xc=np.mean(np.array(points[:,0]))
            yc=np.mean(np.array(points[:,1]))
        cluster_data.append([label, cluster_size, np.array([xc, yc])])

    # Sort clusters by size and take the top two largest clusters
    top_two_clusters = sorted(cluster_data, key=lambda x: x[1], reverse=True)[:2]

    # est_centers = [x[1]*x[2] for x in top_two_clusters]

    # print("n:",np.sum(top_two_clusters,axis=0))
    #print(top_two_clusters)
    tot_n = np.sum([x[1] for x in top_two_clusters])
    #print(tot_n)
    true_center = [x[2]*(x[1]/tot_n) for x in top_two_clusters]

    true_center = np.sum(true_center, axis=0)
    #print(true_center)

    #add radius to the cluster data
    for i in range(len(top_two_clusters)):
        top_two_clusters[i].append((np.linalg.norm(np.array(edge_points[y_pred == top_two_clusters[i][0]]) - true_center))/len(edge_points[y_pred == top_two_clusters[i][0]]))

    top_two_clusters.sort(key=lambda x: x[3], reverse=False)

    # print(top_two_clusters)
    
    if len(top_two_clusters) < 1: 

        print("Less than one clusters found.")
        return None, None

    # Among the top two clusters, select the one with the smallest average radius
    # top_two_clusters.sort(key=lambda x: x[2])
    innermost_label = top_two_clusters[0][0]

    # Extract the points that belong to the innermost circle
    innermost_points = edge_points[y_pred == innermost_label]

    return innermost_points, y_pred


def extract_outermost_circle(edge_points, eps, min_samples):
    # print("got here")
    # DBSCAN clustering
    db = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
    y_pred = db.fit_predict(edge_points)
    unique_labels = set(y_pred)
    unique_labels.discard(-1)

    centroids = []
    average_radii = []
    cluster_data = []

    # Calculate centroids, average radii, and sizes for each cluster
    for label in unique_labels:
        points = edge_points[y_pred == label]
        cluster_size = len(points)
        centroid = np.mean(points, axis=0)
        # print(centroid)
        centroids.append(centroid)

        radii = np.linalg.norm(points - centroid, axis=1)
        average_radius = np.mean(radii)
        average_radii.append(average_radius)

        if cluster_size > 0:
            #xc, yc, _ = estimate_circle_center_and_radius(points)
            xc=np.mean(np.array(points[:,0]))
            yc=np.mean(np.array(points[:,1]))
        cluster_data.append([label, cluster_size, np.array([xc, yc])])

    # Sort clusters by size and take the top two largest clusters
    top_two_clusters = sorted(cluster_data, key=lambda x: x[1], reverse=True)[:2]

    # est_centers = [x[1]*x[2] for x in top_two_clusters]

    # print("n:",np.sum(top_two_clusters,axis=0))
    #print(top_two_clusters)
    tot_n = np.sum([x[1] for x in top_two_clusters])
    #print(tot_n)
    true_center = [x[2]*(x[1]/tot_n) for x in top_two_clusters]

    true_center = np.sum(true_center, axis=0)
    #print(true_center)

    #add radius to the cluster data
    for i in range(len(top_two_clusters)):
        top_two_clusters[i].append((np.linalg.norm(np.array(edge_points[y_pred == top_two_clusters[i][0]]) - true_center))/len(edge_points[y_pred == top_two_clusters[i][0]]))

    top_two_clusters.sort(key=lambda x: x[3], reverse=True)

    #print(top_two_clusters)
    
    if len(top_two_clusters) < 1: 

        print("Less than one clusters found.")
        return None, None

    # Among the top two clusters, select the one with the smallest average radius
    # top_two_clusters.sort(key=lambda x: x[2])
    outermost_label = top_two_clusters[0][0]

    # Extract the points that belong to the innermost circle
    outermost_points = edge_points[y_pred == outermost_label]

    return outermost_points, y_pred


def plot_gamma2_time(result, framerate):
    gamma_2_list = result[0]
    particle_list = result[1]
    n = len(gamma_2_list)
    n_rows = (n + 1) // 2  # Calculate the number of rows needed

    # Adjust the figure size: 16 inches wide, dynamically set the height
    fig_width = 16
    fig_height_per_row = 5  # Increase the height per row for better visibility
    fig, axes = plt.subplots(n_rows, 2, figsize=(fig_width, fig_height_per_row * n_rows))
    axes = axes.ravel()  # Flatten the axes array for easier iteration

    for i in range(n):
        time = np.arange(len(gamma_2_list[i])) / framerate
        y_mean = np.mean(gamma_2_list[i])
        y_std = np.std(gamma_2_list[i])

        # Plot on the ith subplot
        axes[i].plot(time, gamma_2_list[i],'.')  # Added markers for clarity
        axes[i].set_title(f'Gamma2 over Time for Vesicle {particle_list[i]}')
        axes[i].set_xlabel('Time (s)')
        axes[i].set_ylabel('Gamma2')
        axes[i].set_ylim(y_mean - 2 * y_std, y_mean + 2 * y_std)  # Adjust Y-axis limits based on std deviation

    # If the number of plots is odd, hide the last subplot if unused
    if n % 2 != 0:
        axes[-1].axis('off')

    plt.tight_layout()  # Adjust layout to prevent overlap
    plt.show()

def sine_func_freq(x, A, B, C, omega=0.1):  # Here, omega is given a default value of 1.0, but you can replace it with any other value
    return A * np.sin(omega * x + B) + C

def calculate_modulus(framerate,gamma,sigma):
	lower_bounds = [0, 0,-0.1]
	upper_bounds = [np.inf, np.pi,0.1]

	if (type(gamma) is list) == True:
		x=np.arange(0,len(gamma))/framerate
		non_nan_indices = ~np.isnan(gamma)
		x=x[non_nan_indices]
		gamma=np.array(gamma)[non_nan_indices]
		fixed_omega=2 * np.pi / (len(gamma)/framerate)

		# Fit the sine function with the constraints
		params, _ = curve_fit(lambda x, A, B, C: sine_func_freq(x, A, B, C, omega=fixed_omega), x, gamma, 
							  p0=[0.05,2,0], method='trf', 
							  bounds=(lower_bounds, upper_bounds))
		print(fixed_omega)

		storage_modulus=sigma/params[0]*np.cos(np.pi-params[1])
		#storage_modulus_list.append(storage_modulus)
		print('Storage modulus is:'+str(storage_modulus))
		loss_modulus=sigma/params[0]*np.sin(np.pi-params[1])
		#loss_modulus_list.append(loss_modulus)
		print('Loss modulus is:'+str(loss_modulus))

		y_fit = sine_func_freq(x, *params,omega=fixed_omega)

		y=gamma
		residuals = y - y_fit
		ss_res = np.sum(residuals ** 2)
		ss_tot = np.sum((y - np.mean(y)) ** 2)
		r_squared = 1 - (ss_res / ss_tot)
		print('R^2: ' + str(r_squared))

		print(params)
		plt.plot(x, y, 'o', label='Data')
		plt.plot(x, y_fit, label='Fit')
		plt.show()
	else:
		storage_modulus=np.nan
		loss_modulus=np.nan
		fixed_omega=np.nan
		r_squared=np.nan
	return storage_modulus,loss_modulus, fixed_omega, r_squared

# def plot_gamma2_time(gamma_2_list, framerate):
#     for i in range(len(gamma_2_list)):
#         plt.figure(figsize=(8, 5))
#         plt.scatter(np.arange(len(gamma_2_list[i]))/framerate,gamma_2_list[i])
#         plt.title('Gamma2 over Time for vesicle '+str(i))
#         plt.xlabel('Time (s)')
#         plt.ylabel('Gamma2')
#         y_mean = np.mean(gamma_2_list[i])
#         y_std = np.std(gamma_2_list[i])
#         #plt.ylim(-0.1, 0.1)
#         plt.ylim(y_mean-2*y_std, y_mean+2*y_std)

