"""
Class that provides a data structure to handle SCALE-UP geometry files.
"""

# third party imports
import numpy as np
import csv

# package imports
import ezSCUP.settings as cfg
import ezSCUP.exceptions

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# MODULE STRUCTURE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#
# + class Geometry()
#   - __init__(supercell, species, nats)
#   - load_reference(reference_file)
#   - load_restart(restart_file)
#   - load_equilibrium_displacements(partials)
#   - write_restart(restart_file)
#   - write_reference(reference_file)
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class Geometry():

    """
    Geometry container

    # BASIC USAGE # 

    On creation, the class asks for a supercell shape (ie. [4,4,4]),
    the atomic species in each cell (ie. ["Sr", "Ti", "O"]) and the 
    number of atoms per unit cell (ie. 5). It then creates a cell
    structure within the self.cells attribute, containing displacements
    from an unspecified reference structure (they are all zero on creation).
    This attribute may be modified via external access in order to obtain 
    the desired structure.

    The self.read() and self.write() methods provide ways to respectively 
    load and create .restart geometry files for SCALE-UP using this information.
    
    Reads geometry data from a given configuration's .REF file,
    yielding access to its contents through a cell structure within
    the self.cells attribute. Atomic displcements and strains are
    all set to zero by default, until a .restart geometry file is 
    loaded using the self.load_restart() (only one file) or the
    self.load_equilibrium_geometry() (average of several files) methods.

    Basic information about the simulation such as supercell shape,
    number of cells, elements, number of atoms per cell, lattice
    constants and cell information are accessible via attributes.

    # ACCESSING INDIVIDUAL CELL DATA #

    In order to access the data after loading a file just access either 
    the "positions" or "displacements" attributes in the following manner:

        geo = Geometry(...)                             # instantiate the class
        geo.load_reference("example.REF")               # load a .REF file
        geo.load_reference("example.restart")           # load a .restart file
        geo.positions[x,y,z,j,:]                        # position vector of atom j in cell (x,y,z)
        desired_cell.displacements["element_label"]     # displacement vector of atom j in cell (x,y,z)

    Attributes:
    ----------

     - supercell (array): supercell shape
     - ncells (int): number of unit cells
     - nats (int): number of atoms per unit cell
     - nels (int): number of distinct atomic species
     - species (list): atomic species within the supercell
     - elements (list): labels for the atoms within the cells
     - strains (array): supercell strains, in Voigt notation
     - lat_vectors (1x9 array): lattice vectors, in Bohrs 
     - lat_constants (array): xx, yy, zz lattice constants, in Bohrs
     - positions (array): positions of the atoms in the supercell, in Bohrs
     - displacements (array): displacements of the atoms in the supercell, in Bohrs

    """

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

    def __init__(self, supercell, species, nats):

        
        """
        
        Geometry class constructor.

        Parameters:
        ----------

        - supercell (array): supercell shape (ie. [4,4,4])
        - species (list): atomic species within the supercell 
        (ie. ["Sr", "Ti", "O"])
        - - nats (int): number of atoms per unit cell (ie. 5)

        """

        self.supercell = np.array(supercell)
        self.ncells = int(self.supercell[0]*self.supercell[1]*self.supercell[2])
        self.species = species
        self.nels = len(self.species)
        self.nats = nats

        self.strains = np.zeros(6)

        self.lat_vectors = None
        self.lat_constants = None

        self.positions = None
        sc = self.supercell
        self.displacements = np.zeros([sc[0], sc[1], sc[2], self.nats, 3])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

    def reset_geom(self):

        """
        Resets all strain and atomic displacement info back to zero.
        """

        self.strains = np.zeros(6)
        sc = self.supercell
        self.displacements = np.zeros([sc[0], sc[1], sc[2], self.nats, 3])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

    def load_restart(self, restart_file):

        """
        
        Loads the given .restart file's information.

        Parameters:
        ----------

        - restart_file (string): name of the .restart file

        raises: ezSCUP.exceptions.GeometryNotMatching if the geometry contained
        in the .restart file does not match the one loaded from the reference file.

        """

        self.reset_geom()

        f = open(restart_file)
        
        # checks restart file matches loaded geometry
        rsupercell = np.array(list(map(int, f.readline().split())))
        if not np.all(self.supercell == rsupercell): 
            raise ezSCUP.exceptions.GeometryNotMatching()

        rnats, rnels = list(map(int, f.readline().split()))
        if (rnats != self.nats) or (rnels != self.nels):
            raise ezSCUP.exceptions.GeometryNotMatching()

        rspecies = f.readline().split()
        if not (set(rspecies) == set(self.species)):
            raise ezSCUP.exceptions.GeometryNotMatching()

        # read strains 
        self.strains = np.array(list(map(float, f.readline().split())))

        #read displacements
        for x in range(self.supercell[0]):
            for y in range(self.supercell[1]):
                for z in range(self.supercell[2]):
                    # read all atoms within the cell
                    for j in range(self.nats): 
                        line = f.readline().split()
                        self.displacements[x,y,z,j,:] = np.array(list(map(float, line[5:])))

        f.close()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

    def load_reference(self, reference_file):

        """
        
        Loads the given .REF file's information.

        Parameters:
        ----------

        - reference_file (string): name of the .REF file

        raises: ezSCUP.exceptions.GeometryNotMatching if the geometry contained
        in the .restart file does not match the one loaded from the reference file.

        """

        f = open(reference_file)

        # checks restart file matches loaded geometry
        rsupercell = np.array(list(map(int, f.readline().split())))
        if not np.all(self.supercell == rsupercell): 
            raise ezSCUP.exceptions.GeometryNotMatching()

        rnats, rnels = list(map(int, f.readline().split()))
        if (rnats != self.nats) or (rnels != self.nels):
            raise ezSCUP.exceptions.GeometryNotMatching()

        rspecies = f.readline().split()
        if not (set(rspecies) == set(self.species)):
            raise ezSCUP.exceptions.GeometryNotMatching()

        # read lattice vectors
        self.lat_vectors = np.array(list(map(float, f.readline().split())))
        self.lat_constants = np.array([self.lat_vectors[0],self.lat_vectors[4], self.lat_vectors[8]])
        for i in range(self.lat_constants.size): # normalize with supercell size
            self.lat_constants[i] = self.lat_constants[i]/self.supercell[i]

        # generate positions array
        sc = self.supercell
        self.positions = np.zeros([sc[0], sc[1], sc[2], self.nats, 3])
        
        #read reference atomic positions
        for x in range(self.supercell[0]):
            for y in range(self.supercell[1]):
                for z in range(self.supercell[2]):
                    # read all atoms within the cell
                    for j in range(self.nats): 
                        line = f.readline().split()
                        self.positions[x,y,z,j,:] = np.array(list(map(float, line[5:])))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

    def load_equilibrium_displacements(self, partials):

        """
        
        Obtains the equilibrium geometry out of several .restart files
        by averaging out their strains and atomic displacements.

        Parameters:
        ----------

        - partials (list): names of the .restart files.

        raises: ezSCUP.exceptions.RestartNotMatching if the geometry contained in any
        of the .restart file does not match the one loaded from the reference file.

        """
        
        self.reset_geom()

        npartials = len(partials)

        if npartials == 0:
            raise ezSCUP.exceptions.NotEnoughPartials()

        for p in partials: # iterate over all partial .restarts

            f = open(p)
        
            # checks restart file matches loaded geometry
            rsupercell = np.array(list(map(int, f.readline().split())))
            if not np.all(self.supercell == rsupercell): 
                raise ezSCUP.exceptions.GeometryNotMatching()

            rnats, rnels = list(map(int, f.readline().split()))
            if (rnats != self.nats) or (rnels != self.nels):
                raise ezSCUP.exceptions.GeometryNotMatching()

            rspecies = f.readline().split()
            if not (set(rspecies) == set(self.species)):
                raise ezSCUP.exceptions.GeometryNotMatching()

            # add strain contributions
            self.strains += np.array(list(map(float, f.readline().split())))/npartials

            #read displacements
            for x in range(self.supercell[0]):
                for y in range(self.supercell[1]):
                    for z in range(self.supercell[2]):
                        # read all atoms within the cell
                        for j in range(self.nats): 
                            line = f.readline().split()
                            self.displacements[x,y,z,j,:] += np.array(list(map(float, line[5:])))/npartials
    
            f.close()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

    def write_restart(self, restart_file):

        """ 
        
        Writes a .restart file from the current data. 

        Parameters:
        ----------

        - restart_file (string): .restart geometry file where to write everything.
        WARNING: the file will be overwritten.

        """

        f = open(restart_file, 'wt')
        tsv = csv.writer(f, delimiter="\t")

        # write header
        tsv.writerow(list(self.supercell))      
        tsv.writerow([self.nats, self.nels])    
        tsv.writerow(self.species)              
        
        # write strains
        pstrains = list(self.strains)
        pstrains = ["{:.8E}".format(s) for s in pstrains]
        tsv.writerow(pstrains)

        # write displacements
        for x in range(self.supercell[0]):
            for y in range(self.supercell[1]):
                for z in range(self.supercell[2]):
                    for j in range(self.nats):
                        
                        line = [x, y ,z, j+1]

                        if j+1 > self.nels:
                            species = self.nels
                        else:
                            species = j+1
                        
                        line.append(species)

                        disps = list(self.displacements[x,y,z,j,:])
                        disps = ["{:.8E}".format(d) for d in disps]

                        line = line + disps
                    
                        tsv.writerow(line)
        
        f.close()

    def write_reference(self, reference_file):

        """ 
        
        Writes a reference (.REF) file from the current data. 

        Parameters:
        ----------

        - reference_file (string): .REF geometry file where to write everything.
        WARNING: the file will be overwritten.

        """

        if self.positions == None: 
            raise ezSCUP.exceptions.PositionsNotLoaded()

        f = open(reference_file, 'wt')
        tsv = csv.writer(f, delimiter="\t")

        # write header
        tsv.writerow(list(self.supercell))      
        tsv.writerow([self.nats, self.nels])    
        tsv.writerow(self.species)      
        
        # write lattice vectors
        pvectors = list(self.lat_vectors)
        pvectors = ["{:.8E}".format(s) for s in pvectors]
        tsv.writerow(pvectors) 

        # write positions
        for x in range(self.supercell[0]):
            for y in range(self.supercell[1]):
                for z in range(self.supercell[2]):
    
                    for j in range(self.nats):
                        
                        line = [x, y ,z, j+1]

                        if j+1 > self.nels:
                            species = self.nels
                        else:
                            species = j+1
                        
                        line.append(species)

                        disps = list(self.positions[x,y,z,j,:])
                        disps = ["{:.8E}".format(d) for d in disps]

                        line = line + disps
                    
                        tsv.writerow(line)
        
        f.close()

# ================================================================= #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ================================================================= #