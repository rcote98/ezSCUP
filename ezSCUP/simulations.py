"""
Collection of classes to mass-execute ScaleUP simulations.

Classes to execute ScaleUp simulations in a range of 
temperature, strain, stress and electric field settings 
with ease. Each simulation class comes with a parser that 
automates the process of dealing with the output data.
"""

__author__ = "Raúl Coterillo"
__email__  = "raulcote98@gmail.com"
__status__ = "Development"

# third party imports
import numpy as np          # matrix support

# standard library imports
from shutil import move,rmtree      # remove output folder
from pathlib import Path            # general folder management
import os, sys                      # remove files, get pwd
import pickle                       # store parameter vectors

# package imports
from ezSCUP.parsers import REFParser, RestartParser, OutParser
from ezSCUP.generators import RestartGenerator
from ezSCUP.structures import FDFSetting
from ezSCUP.handlers import SCUPHandler
import ezSCUP.settings as cfg
import ezSCUP.exceptions

#####################################################################
## MODULE STRUCTURE
#####################################################################

# class MCSimulation()
# class MCConfiguration()
# class MCSimulationParser()

#####################################################################
## SIMULATIONS (COMPLETE FOLDER)
#####################################################################


class MCSimulation:

    """

    Executes Monte Carlo simulations with the given parameters.
    
    # BASIC USAGE # 
    
    Creates an output folder in the current directory.
    All the simulation data is for each configuration is 
    conveniently stored in subfolders within it:
        
        output / [scale-up system_name].c[n]

    where n is the configuration number. That is, an 8 digit
    integer that specifies the index for each parameter in the
    given simulation, with two digits each in the following order:

        n = [temp][stress][strain][field]
    
    for example, in a simulation with temp=[20,40,60,80] all confs
    simulated at 40K will be stored in folders

        output / [scale-up system_name].c01******

    and so on. The information about the parameters for the simulation
    run is stored in the file:

        output / simulation.info # formated as a pickle file

    In order to access all the simulation output for any given 
    configuration, refer to the class MCSimulationParser in this
    same module.

    # SIMULATION PARAMETER SPECIFICATION #

    - Temperature (temp):
        List of temperatures, in K
            i.e:temp = np.linspace(20,100,5)
                temp = [27, 45, 36]

    - External Stress (stress):
        List of stress vectors in Voigt notation, in GPa
            i.e:stress = [
                [10., 0., 0., 0., 0., 0.],
                [0., 10., 0., 0., 0., 0.],
                [0., 0., 10., 0., 0., 0.]
            ]   # 10 GPa strains in each direction

    - Strains (strain):
        List of strain vectors in Voigt notation, in percentual change
            i.e:strain = [
                [+0.02, +0.02, 0., 0., 0., 0.],
                [+0.00, +0.00, 0., 0., 0., 0.],
                [-0.02, -0.02, 0., 0., 0., 0.]
            ]   # +-2% and 0% cell strain in the x and y direction

    - Static Electric Field (field):
        List of electric field vectors, in V/m
            i.e:field = [
                [1e9, 0., 0.]
            ]   # 1e9 V/m = 1V/nm in the x direction  
    
    """

    ########################
    #      ATTRIBUTES      #
    ########################

    fdf = ""            # base fdf file
    name = ""           # default fdf's system_name

    temp = []           # temperature vectors (K) 
    stress = []         # stress vectors (Gpa)
    strain = []         # strain vectors (% change) 
    field = []          # electric field vectors (V/m)

    OVERWRITE = False   # whether to overwrite latest output

    def __init__(self, supercell, elements, nats, OVERWRITE=False):

        """
        MCSimulation class constructor. 
        
        Requires supercell information in order to generate
        the .restart files required to set strains.  

        Parameters:
        ----------

        - supercell  (3x1 array): supercell size

        - elements (list): element labels, 
            ie: SrTiO3 -> elements = ["Sr", "Ti", "O"]

        - nats (int): number of atoms inside a unit cell, 
            ie: SrTi03 -> nats = 5

        - OVERWRITE (boolean): whether or not overwrite
            existing output folder, defaults to False.
        """

        self.supercell = supercell
        self.elements = elements
        self.nats = nats

        self.OVERWRITE = OVERWRITE

    #######################################################


    def launch(self, fdf, temp, stress=None, strain=None, field=None):

        """
        
        Start a simulation run with all the possible combinations of
        the given parameters. 

        For more information on variable definition, 
        see the class docstring.

        Parameters:
        ----------

        - fdf  (string): common fdf base file for all simulations.

        - temp (list): list of temperatures, required.

        - stress (list): list of stress vectors, if needed.

        - strain (list): list of strain vectors, if needed.

        - field (list): list of field vectors, if needed.

        """

        # first and foremost, check if a valid 
        # ScaleUP executable has been configured.
        if cfg.SCUP_EXEC == None:

            print("""
            WARNING: No executable detected

            A path for a valid ScaleUP executable
            must be provided before any simulations
            are carried out.

            In order to do this, include the lines

            import ezSCUP.settings as cfg
            cfg.SCUP_EXEC=[path_to_exec]

            at the beginning of your script.
            """)

            raise ezSCUP.exceptions.NoSCUPExecutableDetected

        #  the main fdf file
        self.fdf = fdf

        # temperature vector, required
        self.temp = np.array(temp)

        # stress vector, optional
        if stress == None:
            self.stress = [np.zeros(6)]
        else:
            self.stress = [np.array(p, dtype=np.float64) for p in stress]

        # strain vector list, optional
        if strain == None:
            self.strain = [np.zeros(6)]
        else:
            self.strain = [np.array(s, dtype=np.float64) for s in strain]

        """ STRAIN BLOCK EXAMPLE FDF
        this sets only which components
        shall vary in the MC run

        %block fix_strain_component
        T T F F F T
        %endblock fix_strain_component
        """
        
        # electric field vector list, optional
        if field == None:
            self.field = [np.zeros(3)]
        else:
            self.field = [np.array(f, dtype=np.float64) for f in field]

        # get the current path
        current_path = os.getcwd()


        # create output directory
        try:
            main_output_folder = os.path.join(current_path, "output")
            os.makedirs(main_output_folder)
        except FileExistsError: # check whether directory already exists
            if self.OVERWRITE:
                print("""
                Found existing output folder,
                all its contents are now lost.
                Reason: OVERWRITE set to True.
                """)
                rmtree(main_output_folder)
                print("")
                pass
            else:
                print("""
                Found existing output folder,
                skipping simulation process.
                Reason: OVERWRITE set to False.
                """)
                return 0 # exits simulation process

        # load main fdf file
        sim = SCUPHandler(scup_exec=cfg.SCUP_EXEC)
        sim.load(self.fdf)

        # adjust the supercell
        sim.settings["supercell"] = list(self.supercell)

        # modify FDF according to ezSCUP.settings
        if cfg.MC_STEPS != None:
            sim.settings["mc_nsweeps"].value = int(cfg.MC_STEPS)
        if cfg.MC_STEP_INTERVAL != None:
            sim.settings["n_write_mc"].value = int(cfg.MC_STEP_INTERVAL)
        if cfg.MC_MAX_JUMP != None:
            sim.settings["mc_max_step_d"].value = float(cfg.MC_MAX_JUMP)
        if cfg.LATTICE_OUTPUT_INTERVAL != None:
            sim.settings["print_std_lattice_nsteps"].value = int(cfg.LATTICE_OUTPUT_INTERVAL)
        if cfg.FIXED_STRAIN_COMPONENTS != None:
            if len(cfg.FIXED_STRAIN_COMPONENTS) != 6:
                raise ezSCUP.exceptions.InvalidFDFSetting
            setting = []
            for s in list(cfg.FIXED_STRAIN_COMPONENTS):
                if not isinstance(s, bool):
                    raise ezSCUP.exceptions.InvalidFDFSetting
                if s:
                    setting.append("T")
                else:
                    setting.append("F")
            sim.settings["fix_strain_component"] = setting

        # check is strains are needed and creates generator
        if strain != None:
            sim.settings["geometry_restart"] = FDFSetting("temp.restart")
            gen = RestartGenerator(self.supercell, self.elements, self.nats)

        # print common simulation settings
        print("\nCommon simulation settings:")
        sim.print_all()
        print("")

        # load simulation name
        self.name = sim.settings["system_name"].value
        
        # simulation counters
        total_counter   =  0

        # total number of simulations 
        nsims = self.temp.size*len(self.strain)*len(self.field)*len(self.stress)
        print("\nStarting calculations...\n")

        for t in self.temp:
            temp_counter = np.where(self.temp == t)[0][0]
            for p in self.stress:
                stress_counter = [np.array_equal(p,x) for x in self.stress].index(True)
                for s in self.strain:
                    strain_counter = [np.array_equal(s,x) for x in self.strain].index(True)
                    for f in self.field:
                        field_counter = [np.array_equal(f,x) for x in self.field].index(True)

                        total_counter += 1

                        print("##############################")
                        print("Configuration " + str(total_counter) + " out of " + str(nsims))
                        print("Temperature:",   str(t),"K")
                        print("Stress:",        str(p),"GPa")
                        print("Strain:",        str(s), r"% change")
                        print("Electric Field:",str(f), "V/m")
                        print("##############################")

                        # file base name
                        sim_name = self.name + "T{:d}".format(int(t))
                        sim.settings["system_name"].value = sim_name

                        # configuration name
                        conf_name = "c{:02d}{:02d}{:02d}{:02d}".format(temp_counter,
                            stress_counter, strain_counter, field_counter)

                        # subfolder name
                        subfolder_name = self.name + "." + conf_name

                        # modify target temperature
                        sim.settings["mc_temperature"].value = t

                        # modify target stress, if needed
                        if stress != None: 
                            sim.settings["external_stress"] = [p]

                        # set target strain, if needed
                        if strain != None:
                            gen.strains = s
                            gen.write("temp.restart")

                        # modify target field, if needed
                        if field != None: 
                            sim.settings["static_electric_field"] = [f]

                        # define human output filename
                        output = sim_name + ".out"

                        # simulate the current configuration
                        sim.launch(output_file=output)

                        # move all the output to its corresponding folder
                        output_folder = os.path.join(main_output_folder, subfolder_name)
                        os.makedirs(output_folder)

                        files = os.listdir(current_path)
                        for f in files:
                            if sim_name in f:
                                move(f, output_folder)

                        print("\nAll files stored in output/" + subfolder_name + " succesfully.\n")

        # save simulation setup file 
        print("Saving simulation setup file... ")

        setup = {
            "name": self.name,
            "supercell": self.supercell,
            "elements": self.elements,
            "nats": self.nats,
            "temp": self.temp,
            "strain": self.strain,
            "stress": self.stress,
            "field": self.field
            }

        simulation_setup_file = os.path.join(main_output_folder, cfg.SIMULATION_SETUP_FILE)

        with open(simulation_setup_file, "wb") as f:
            pickle.dump(setup, f)

        print("")

        # cleanup
        if strain != None:
            os.remove("temp.restart")

        print("Simulation process complete!")

    #######################################################

#####################################################################
## MONTE CARLO CONFIGURATION (FOLDER-WISE MANAGEMENT)
#####################################################################

class MCConfiguration:

    """

    Parses all the data from a previously simulated configuration, 
    providing easy access to all its output. 
    
    # BASIC USAGE # 
    
    Reads simulation data from a given configuration (subfolder) in the
    output folder. By default this class starts empty, until a folder
    is loaded with the load() method.

    Basic information about the simulation such as supercell shape,
    original lattice constants, elements information and number of
    atoms in the unit cell are accessible via attributes.

    The MC .partial file data is averaged out and stored in self.strains
    and self.cells. More on cell information storage in ezSCUP.structures.

    All the output file information is accessed through the output_file()
    method, which returns a pandas Dataframe with the lattice ("LT:") data.

    # ACCESSING CELL DATA #

    # TODO copy from the parser classes

    """

    ########################
    #      ATTRIBUTES      #
    ########################

    name = ""               # file base name
    folder_name = ""        # configuration folder name
    folder_path = ""        # configuration folder path
    current_directory = ""  # main script directory
    partials = []           # partial files in the folder (full path)

    nmeas = 0               # number of measurements
    total_steps = 0         # number of MC steps
    # only pick partials with higher step than this
    step_threshold = cfg.MC_EQUILIBRATION_STEPS

    supercell = []          # supercell shape
    lat_constants = []      # lattice constants, in Bohr
    elements = []           # elements in the lattice
    nats = 0                # number of atoms per cell
    
    strains = []            # average relative strains 
    cells = []              # average cell data    

    refp = REFParser()      # .restart file parser
    resp = RestartParser()  # .REF file parser
    outp = OutParser()      # output file parser

    #######################################################

    def load(self, folder_name, base_sim_name, config_data=None):

        """
        
        Load the given configuration folder's data.

        Parameters:
        ----------

        - folder_name  (string): configuration folder name,
            usually [ScaleUP system_name].c[configuration number]

        - base_sim_name (list): basename of the ScaleUP files,
            usually [ScaleUP system_name].T[temperature in integer format]

        """

        # loads basic filename information
        self.name = base_sim_name
        self.folder_name = folder_name
        self.current_directory = os.getcwd()

        folder = os.path.join(self.current_directory, "output", folder_name)
        self.folder_path = folder

        # partial .restart files for each MC interval
        partials = [k for k in os.listdir(folder) if 'partial' in k]
        partials = sorted([k for k in partials if '.restart' in k])
        self.partials = [os.path.join(self.folder_path, p) for p in partials]

        # get total number of steps
        self.total_steps = max([int(p[len(base_sim_name)+10:-8]) for p in partials])
        self.step_threshold = cfg.MC_EQUILIBRATION_STEPS 

        # check if any measurements are taken into consideration
        if (self.total_steps <= self.step_threshold):
            print("Step threshold {:d} greater than total steps ({:d}):".format(self.step_threshold, self.total_steps))
            print(r"Reducing to 20% of total steps.")
            self.step_threshold = int(0.2*self.total_steps)
        
        # selects only partials above self.step_threshold steps
        step_filter = [int(p[len(base_sim_name)+10:-8]) > self.step_threshold for p in partials]
        
        partials = [p for i, p in enumerate(partials) if step_filter[i]]

        # number of partials selected
        self.nmeas = len(partials)

        # loads cells with only their original location
        self.refp.load(os.path.join(folder, base_sim_name + "_FINAL.REF"))
        self.supercell = self.refp.supercell
        self.elements = self.refp.elements
        self.cells = self.refp.cells
        self.nats = self.refp.nats

        ####### obtain average strains and displacements #######

        # first, initialize the attributes for strain and displacements
        self.strains = np.zeros(6)
        for x in range(self.supercell[0]):
            for y in range(self.supercell[1]):
                for z in range(self.supercell[2]):

                    self.cells[x,y,z].displacements = {}
                    for atom in self.cells[x,y,z].pos:
                        self.cells[x,y,z].displacements[atom] = np.zeros(3)

        # add all strains and displacements
        for f in partials: # over all partial .restarts

            self.resp.load(os.path.join(folder, f)) # load the partial
            self.strains += self.resp.strains # add the strains

            for x in range(self.supercell[0]):
                for y in range(self.supercell[1]):
                    for z in range(self.supercell[2]):
                        for atom in self.cells[x,y,z].disp: 
                            self.cells[x,y,z].displacements[atom] += self.resp.cells[x,y,z].displacements[atom]

        # divide by the number of measurementes
        self.strains = self.strains/self.nmeas

        for x in range(self.supercell[0]):
                for y in range(self.supercell[1]):
                    for z in range(self.supercell[2]):
                        for atom in self.cells[x,y,z].disp: 
                            self.cells[x,y,z].displacements[atom] = self.cells[x,y,z].displacements[atom]/self.nmeas
        

    #######################################################

    def lattice_output(self):
        
        """

        Load the given configuration lattice data from its output file.

        Return:
        ----------
            - a pandas Dataframe with the lattice output data.
        """

        self.step_threshold = cfg.MC_EQUILIBRATION_STEPS

        out_file = os.path.join(self.folder_path, self.name + ".out")
        self.outp.load(out_file)

        ldata = self.outp.lattice_data.copy(deep=True)
        ldata = ldata[ldata.index >= self.step_threshold]

        return self.outp.lattice_data

    #######################################################

    def print_all(self):

        """ Prints all available configuration info. """

        print("Configuration name: " + self.folder_name + "\n")
        print("Total MC steps:" + str(self.total_steps))
        print("Eq. steps: " + str(self.step_threshold))
        print("Supercell shape: " + str(self.supercell))
        print("Atoms per cell: " + str(self.nats))
        print("Elements in cell:")
        print(self.elements)
        print("Average cell strains:") 
        print(self.strains)
        print("")
        for c in self.cells:
            print(self.cells[c])
            self.cells[c].print_atom_pos()
            self.cells[c].print_atom_disp()
            print("")

    #######################################################

#####################################################################
## SIMULATION PARSER (WHOLE OUTPUT FOLDER MANAGEMENT)
#####################################################################        

class MCSimulationParser:

    """

    Parses all the data from a previously simulated configuration, 
    providing easy access to all its output. 
    
    # BASIC USAGE # 
    
    Reads simulation data from a given configuration (subfolder) in the
    output folder. By default this class starts empty, until a folder
    is loaded with the load() method.

    Basic information about the simulation such as supercell shape,
    original lattice constants, elements information and number of
    atoms in the unit cell are accessible via attributes.

    The MC .partial file data is averaged out and stored in self.strains
    and self.cells. More on cell information storage in ezSCUP.structures.

    All the output file information is accessed through the output_file()
    method, which returns a pandas Dataframe with the lattice ("LT:") data.

    """

    ########################
    #      ATTRIBUTES      #
    ########################

    name = ""           # file base name

    temp = []           # temperature vectors (K) 
    stress = []         # stress vectors (Gpa)
    strain = []         # strain vectors (% change) 
    field = []          # electric field vectors (V/m)

    parser = MCConfiguration()

    #######################################################

    def __init__(self):

        # check if there's an output folder
        if os.path.exists(os.path.join(os.getcwd(), "output")):
            self.index() # loads the simulation.info from the output folder
        else:
            raise ezSCUP.exceptions.OutputFolderDoesNotExist

    def index(self):

        # get the current path
        current_path = os.getcwd()

        # main output folder
        main_output_folder = os.path.join(current_path, "output")

        # simulation setup file 
        simulation_setup_file = os.path.join(main_output_folder, cfg.SIMULATION_SETUP_FILE)

        # load simulation setup file 
        with open(simulation_setup_file, "rb") as f:
            setup = pickle.load(f) 

        # load run information
        self.name      = setup["name"] 
        self.supercell = setup["supercell"]
        self.elements  = setup["elements"]
        self.nats      = setup["nats"]

        # load simulation parameters
        self.temp   = setup["temp"] 
        self.stress = setup["stress"] 
        self.strain = setup["strain"] 
        self.field  = setup["field"] 

    #######################################################

    def access(self, t, p=None, s=None, f=None):

        # stress vector, optional
        if p == None:
            p = np.zeros(6)
        else:
            p = np.array(p)

        # strain vector list, optional
        if s == None:
            s = np.zeros(6)
        else:
            s = np.array(s)
        
        # electric field vector list, optional
        if f == None:
            f = np.zeros(3)
        else:
            f = np.array(f)

        # obtain index of desired parameters
        try: 
            t_index = np.where(self.temp == t)[0][0]
            p_index = [np.array_equal(p,x) for x in self.stress].index(True)
            s_index = [np.array_equal(s,x) for x in self.strain].index(True)
            f_index = [np.array_equal(f,x) for x in self.field].index(True)
        except:
            raise ezSCUP.exceptions.InvalidMCConfiguration(
                "The configuration has not been simulated."
            )

        # get configuration name
        conf_name = "c{:02d}{:02d}{:02d}{:02d}".format(t_index, 
            p_index, s_index, f_index)

        # subfolder name
        subfolder_name = self.name + "." + conf_name
        sim_name = self.name + "T{:d}".format(int(t))

        self.parser.load(subfolder_name, sim_name)
        
        return self.parser

    #######################################################
        