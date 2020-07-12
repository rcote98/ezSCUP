"""Example script"""

__author__ = "Raúl Coterillo"
__email__  = "raulcote98@gmail.com"
__status__ = "Development"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~~~~~~~~~~~~~~ REQUIRED MODULE IMPORTS ~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# standard library imports
import os, sys
import time

# third party imports
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np

# ezSCUP imports
from ezSCUP.simulations import MCSimulation, MCConfiguration, MCSimulationParser
from ezSCUP.analysis import perovskite_AFD, perovskite_simple_rotation, BornPolarization
from ezSCUP.files import save_file
import ezSCUP.settings as cfg

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~ USER DEFINED SETTINGS ~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# IMPORTANT: location of the Scale-Up executable in the system
cfg.SCUP_EXEC = "/home/citimac/jjunquer/Code/Git/scaleup/Obj/Intel-Parallel-OpenMP/src/scaleup.x"

OVERWRITE = False                           # overwrite old output folder?

SUPERCELL = [8,8,8]                         # shape of the supercell
ELEMENTS = ["Sr", "Ti", "O"]                # elements in the lattice
NATS = 5                                    # number of atoms per cell

TEMPERATURES = np.linspace(20, 260, 13)     # temperatures to simulate         

cfg.MC_STEPS = 40000                        # MC total steps
cfg.MC_EQUILIBRATION_STEPS = 25000           # MC equilibration steps
cfg.MC_STEP_INTERVAL = 50                   # MC steps between partial files
cfg.LATTICE_OUTPUT_INTERVAL = 25            # MC steps between output prints  
cfg.FIXED_STRAIN_COMPONENTS = [False]*6     # fixed strain components (none)

plot_AFDa =   False                          # plot AFDa distortion angles?
plot_AFDi =   False                          # plot AFDi distortion angles?
plot_FE = True
plot_polarizarion = True
plot_strain = False                          # plot strains?
plot_vectors = False                        # plot vector fields?
# temperatures for which to plot rotation vector field
VECTOR_TEMPS = [TEMPERATURES[0]] 

show_plots =  True                          # show the created plots?

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~ code starts here ~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


#####################################################################
#              FUNCTIONS TO OBTAIN THE AFD ROTATIONS                #
#####################################################################

def read_AFD(temp, mode="a"):

    """ Calculates the average AFD rotation for each temperature. """

    if mode != "a" and mode != "i":
        raise NotImplementedError

    # create a simulation parser
    sim = MCSimulationParser()

    ###################

    rotations = []
    rotations_err = []
    for t in temp: # read all files

        # Ox, Oy, Oz = O3, O2, O1
        config = sim.access(t)
        labels = ["Sr", "Ti", "O3", "O2", "O1"]

        x_angles, y_angles, z_angles = perovskite_AFD(config, labels, mode)

        x_axis_rot = np.mean(np.abs(x_angles))
        x_axis_rot_err = np.std(np.abs(x_angles))
 
        y_axis_rot = np.mean(np.abs(y_angles))
        y_axis_rot_err = np.std(np.abs(y_angles))

        z_axis_rot = np.mean(np.abs(z_angles))
        z_axis_rot_err = np.std(np.abs(z_angles))

        rots = np.array([x_axis_rot, y_axis_rot, z_axis_rot])
        rots_err = np.array([x_axis_rot_err, y_axis_rot_err, z_axis_rot_err])
    
        main_axis = np.argmax(rots)

        if main_axis == 2:
            rotations.append(rots)
            rotations_err.append(rots_err)
        elif main_axis == 1:
            rotations.append(np.array([z_axis_rot, x_axis_rot, y_axis_rot]))
            rotations_err.append(np.array([z_axis_rot_err, x_axis_rot_err, y_axis_rot_err]))
        else:
            rotations.append(np.array([y_axis_rot, z_axis_rot, x_axis_rot]))
            rotations_err.append(np.array([y_axis_rot_err, z_axis_rot_err, x_axis_rot_err]))

    return np.array(rotations), np.array(rotations_err)

def display_AFD(temp, mode="a"):

    """ Generates the AFD distortion graph. """

    # calculating angles from output files
    if mode == "a":
        angles, angles_err = read_AFD(temp, mode="a")
    elif mode == "i":
        angles, angles_err = read_AFD(temp, mode="i")
    else:
        raise NotImplementedError
    
    # unpack the rotations
    xrot = angles[:,0]
    yrot = angles[:,1]
    zrot = angles[:,2]

    xrot_err = angles_err[:,0]
    yrot_err = angles_err[:,1]
    zrot_err = angles_err[:,2]

    headers = ["temp", "xrot", "yrot", "zrot",
        "xrot_err", "yrot_err", "zrot_err"]
    save_file("csv/AFD" + mode + ".csv", headers, 
        [temp, xrot, yrot, zrot, xrot_err, yrot_err, zrot_err])

    # plotting
    
    fig = plt.figure("AFD" + mode + ".png")

    plt.errorbar(temp, xrot, yerr=xrot_err, label=r"AFD$_{x}^{" + mode + "}$", marker ="<") 
    plt.errorbar(temp, yrot, yerr=yrot_err, label=r"AFD$_{y}^{" + mode + "}$", marker =">") 
    plt.errorbar(temp, zrot, yerr=zrot_err, label=r"AFD$_{z}^{" + mode + "}$", marker ="^")
    
    plt.tight_layout(pad = 3)

    plt.xlabel("T (K)", fontsize = 14)
    plt.ylabel(r"$AFD^{" + mode + "}$ (deg)", fontsize = 14)

    plt.ylim(0,8)
    
    plt.legend(frameon = True, fontsize = 14)
    plt.grid(True)

    plt.savefig("plots/AFD" + mode + ".png")
    plt.draw()


#####################################################################
#                 FUNCTIONS TO OBTAIN THE POLARIZATION              #
#####################################################################

def read_polarization(temps, module=False):

    """ Calculates the average strains for each temperature. """

    sim = MCSimulationParser()
    born = BornPolarization()
    sim.index()


    labels = ["Sr", "Ti", "O3", "O2", "O1"]
    born_charges = {
        "Sr": np.array([2.566657, 2.566657, 2.566657]),
        "Ti": np.array([7.265894, 7.265894, 7.265894]),
        "O3": np.array([-5.707345, -2.062603, -2.062603]),
        "O2": np.array([-2.062603, -5.707345, -2.062603]),
        "O1": np.array([-2.062603, -2.062603, -5.707345]),
    }

    pols = []
    pols_err = []
    for t in temps: # read all files

        config = sim.access(t)
        born.load(config)
        polx, poly, polz = born.perovs_unit_cell_polarization(born_charges)

        if module:
            px = np.mean(np.abs(polx))
            py = np.mean(np.abs(poly))
            pz = np.mean(np.abs(polz))

            px_err = np.std(np.abs(polx))
            py_err = np.std(np.abs(poly))
            pz_err = np.std(np.abs(polz))
        else:
            px = np.mean(polx)
            py = np.mean(poly)
            pz = np.mean(polz)

            px_err = np.std(polx)
            py_err = np.std(poly)
            pz_err = np.std(polz)


        pol = np.array([px,py,pz])
        pol_err = np.array([px_err,py_err,pz_err])
        
        pols.append(pol)
        pols_err.append(pol_err)

    return np.array(pols), np.array(pols_err)


def display_polarization(temps, module=False):

    """Generates the strains graph."""

    pols, pols_err = read_polarization(temps, module) # reading cell sizes from output files

    # unpacking the cell parameters
    px = pols[:,0]
    py = pols[:,1]
    pz = pols[:,2]

    px_err = pols_err[:,0]
    py_err = pols_err[:,1]
    pz_err = pols_err[:,2]


    headers = ["temp", "px", "py", "pz",
        "px_err", "py_err", "pz_err"]

    if module:
        save_file("csv/abs_polarization.csv", headers, 
            [temps, px, py, pz, px_err, py_err, pz_err,])
    else:
        save_file("csv/polarization.csv", headers, 
            [temps, px, py, pz, px_err, py_err, pz_err,])

    # plotting 
    plt.figure("polarization.png")

    plt.errorbar(temps, px, yerr=px_err, label=r"$P_x$", marker ="<") 
    plt.errorbar(temps, py, yerr=py_err, label=r"$P_y$", marker =">") 
    plt.errorbar(temps, pz, yerr=pz_err, label=r"$P_z$", marker ="^")

    plt.tight_layout(pad = 3)

    plt.ylabel(r"$P$ (C/m)", fontsize = 14)
    plt.xlabel("T (K)", fontsize = 14)
    
    plt.legend(frameon = True, fontsize = 14)
    plt.grid(True)
    
    if module:
        plt.savefig("plots/abs_polarization.png")
    else:
        plt.savefig("plots/polarization.png")

    plt.draw()


#####################################################################
#                 FUNCTIONS TO OBTAIN THE STRAINS                   #
#####################################################################

def read_strain(temps):

    """ Calculates the average strains for each temperature. """

    sim = MCSimulationParser()
    sim.index()

    strains = []
    strains_err = []
    for t in temps: # read all files

        sim.access(t)
        data = sim.parser.lattice_output()

        # rolling(40).mean()

        plt.figure(int(t))
        plt.plot(data["Strn_xx"], label="x")
        plt.plot(data["Strn_yy"], label="y")
        plt.plot(data["Strn_zz"], label="z")
        plt.legend()
        plt.savefig("plots/test/t{:d}.png".format(int(t)))
        plt.close()

        sx = data["Strn_xx"].mean()
        sy = data["Strn_yy"].mean()
        sz = data["Strn_zz"].mean()

        sx_err = data["Strn_xx"].std()
        sy_err = data["Strn_yy"].std()
        sz_err = data["Strn_zz"].std()
        
        # rotate to take the z strain as the maximum     
        stra = np.array([sx,sy,sz])
        stra_err = np.array([sx_err,sy_err,sz_err])
        
        main_axis = np.argmax(stra)

        if main_axis == 2:
            strains.append(stra)
            strains_err.append(stra_err)
        elif main_axis == 1:
            strains.append(np.array([sz, sx, sy]))
            strains_err.append(np.array([sz_err, sx_err, sy_err]))
        else:
            strains.append(np.array([sy, sz, sx]))
            strains_err.append(np.array([sy_err, sz_err, sx_err]))

    return np.array(strains), np.array(strains_err)


def display_strain(temps):

    """Generates the strains graph."""

    strain, strain_err = read_strain(temps) # reading cell sizes from output files

    # unpacking the cell parameters
    sx = strain[:,0]
    sy = strain[:,1]
    sz = strain[:,2]

    sx_err = strain_err[:,0]
    sy_err = strain_err[:,1]
    sz_err = strain_err[:,2]

    print("c/a = " + str(np.mean((1+sz)/(1+sx))))

    headers = ["temp", "sx", "sy", "sz",
        "sx_err", "sy_err", "sz_err"]
    save_file("csv/strain.csv", headers, 
        [temps, sx, sy, sz, sx_err, sy_err, sz_err,])

    # plotting 
    plt.figure("strain.png")

    plt.errorbar(temps, sx, yerr=sx_err, label=r"$\eta_x$", marker ="<") 
    plt.errorbar(temps, sy, yerr=sy_err, label=r"$\eta_y$", marker =">") 
    plt.errorbar(temps, sz, yerr=sz_err, label=r"$\eta_z$", marker ="^")

    plt.tight_layout(pad = 3)

    plt.ylabel(r"$\eta$ (%)", fontsize = 14)
    plt.xlabel("T (K)", fontsize = 14)
    
    plt.legend(frameon = True, fontsize = 14)
    plt.grid(True)
    
    plt.savefig("plots/strain.png")
    plt.draw()


#####################################################################
#                       MAIN FUNCTION CALL                          #
#####################################################################

if __name__ == "__main__":

    # create simulation class
    #sim = MCSimulation(SUPERCELL, ELEMENTS, NATS, OVERWRITE)

    # simulate and properly store output
    #sim.launch("input.fdf", temp=TEMPERATURES)

    try: #create the "plots" folder if needed
        os.mkdir("plots")
    except FileExistsError:
        pass
    

    try: # create the "csv" folder if needed
        os.mkdir("csv")
    except FileExistsError:
        pass

    if plot_AFDa: # plot AFDa if needed
        print("\nGenerating AFDa plot...")
        start = time.time()
        display_AFD(TEMPERATURES, mode="a")
        end = time.time()
        print("\n DONE! Time elapsed: {:.3f}s".format(end-start))

    if plot_AFDi: # plot AFDi if needed
        print("\nGenerating AFDi plot...")
        start = time.time()
        display_AFD(TEMPERATURES, mode="i")
        end = time.time()
        print("\n DONE! Time elapsed: {:.3f}s".format(end-start))

    if plot_strain: # plot strain if needed
        print("\nGenerating strain plot...")
        start = time.time()
        display_strain(TEMPERATURES)
        end = time.time()
        print("\n DONE! Time elapsed: {:.3f}s".format(end-start))


    if plot_polarizarion: # plot strain if needed
        print("\nGenerating polarization plot...")
        start = time.time()
        display_polarization(TEMPERATURES, module=True)
        end = time.time()
        print("\n DONE! Time elapsed: {:.3f}s".format(end-start))

   
    if show_plots:
        print("\n Displaying selected plots...")
        plt.show()
    
    print("\nEVERYTHING DONE!")

#####################################################################