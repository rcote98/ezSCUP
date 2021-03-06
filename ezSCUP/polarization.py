"""
Several functions to calculate supercell polarization.
"""

# third party imports
import numpy as np

# package imports
from ezSCUP.geometry import Geometry

import ezSCUP.settings as cfg
import ezSCUP.exceptions

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# MODULE STRUCTURE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#
# + func unit_conversion(scup_polarization)
# + func polarization(config, born_charges)
# + func stepped_polarization(config, born_charges)
# + func layered_polarization(config, born_charges)
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def unit_conversion(scup_polarization):

    """
    Converts polarizations from e/bohr2 to C/m2.

    Parameters:
    ----------
    - scup_polarization (float): polarization in e/bohr2

    Return:
    ----------
    - same polarization in C/m2.

    """

    e2C = 1.60217646e-19 # elemental charges to Coulombs
    bohr2m = 5.29177e-11 # bohrs to meters

    return scup_polarization*e2C/bohr2m**2 # polarization in C/m2

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def polarization(geom, born_charges):

    """

    Calculates supercell polarization in the current configuration
    using the given effective charge vector.

    Parameters:
    ----------
    - born_charges (dict): dictionary with element labels as keys
    and effective charge 3D vectors as values. (in elemental charge units)

    Return:
    ----------
    - a 3D vector with the macroscopic polarization (in C/m2)
    
    """

    if not isinstance(geom, Geometry):
        raise ezSCUP.exceptions.InvalidGeometryObject

    labels = list(born_charges.keys())

    if len(labels) != 5:
        raise ezSCUP.exceptions.InvalidLabelList

    for l in labels:
        if l >= geom.nats:
            raise ezSCUP.exceptions.AtomicIndexOutOfBounds

    
    cnts = geom.lat_constants
    stra = geom.strains

    ucell_volume = (cnts[0]*(1+stra[0]))*(cnts[1]*(1+stra[1]))*(cnts[2]*(1+stra[2]))
    volume = geom.ncells*ucell_volume

    pol = np.zeros(3)
    for x in range(geom.supercell[0]):
        for y in range(geom.supercell[1]):
            for z in range(geom.supercell[2]):

                for l in labels:

                    tau = geom.displacements[x,y,z,l,:]
                    charges = born_charges[l]
                    
                    for i in range(3):
                        pol[i] += charges[i]*tau[i]

    pol = pol/volume # in e/bohr2

    return unit_conversion(pol) # in C/m2

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def stepped_polarization(supercell, species, nats, lat_cts, partials, born_charges):

    """

    Calculates supercell polarization in the current configuration
    for every single .partial file using the given Born effective charges.

    Parameters:
    ----------
    - born_charges (dict): dictionary with element labels as keys
    and effective charge 3D vectors as values. (in elemental charge units)

    Return:
    ----------
    - a list of 3D vectors with the macroscopic polarization (in C/m2)

    """

    labels = list(born_charges.keys())

    for l in labels:
        if l >= nats:
            raise ezSCUP.exceptions.AtomicIndexOutOfBounds
    
    cnts = lat_cts
    geom = Geometry(supercell, species, nats)

    pol_hist = []
    for f in partials:
        
        geom.load_restart(f)

        stra = geom.strains

        ucell_volume = (cnts[0]*(1+stra[0]))*(cnts[1]*(1+stra[1]))*(cnts[2]*(1+stra[2]))
        volume = geom.ncells*ucell_volume

        pol = np.zeros(3)
        for x in range(geom.supercell[0]):
            for y in range(geom.supercell[1]):
                for z in range(geom.supercell[2]):

                    for l in labels:
                        tau = geom.displacements[x,y,z,l,:]
                        charges = born_charges[l]
                        
                        for i in range(3):
                            pol[i] += charges[i]*tau[i]

        pol = pol/volume # in e/bohr2
        pol_hist.append(unit_conversion(pol)) # in C/m2
  
    return pol_hist

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
'''
def layered_polarization(config, born_charges):

    """

    Calculates supercell polarization in the current configuration
    in horizontal (z-axis) layers using the given effective charges.

    Parameters:
    ----------
    - born_charges (dict): dictionary with element labels as keys
    and effective charge 3D vectors as values. (in elemental charge units)

    Return:
    ----------
    - a list of 3D vectors with the macroscopic polarization (in C/m2)
    
    """

    if not isinstance(config, MCConfiguration):
        raise ezSCUP.exceptions.InvalidMCConfiguration

    labels = list(born_charges.keys())

    for l in labels:
        if l not in config.geo.elements:
            raise ezSCUP.exceptions.InvalidLabel

    
    cnts = config.geo.lat_constants
    stra = config.geo.strains
    ncells_per_layer = config.geo.supercell[0]*config.geo.supercell[1]

    ucell_volume = (cnts[0]*(1+stra[0]))*(cnts[1]*(1+stra[1]))*(cnts[2]*(1+stra[2]))
    volume = ucell_volume*ncells_per_layer

    pols_by_layer = []
    for layer in range(config.geo.supercell[2]):

        pol = np.zeros(3)
        for x in range(config.geo.supercell[0]):
            for y in range(config.geo.supercell[1]):

                for label in config.geo.elements:

                    tau = config.geo.cells[x,y,layer].displacements[label]
                    charges = born_charges[label]
                    
                    for i in range(3):
                        pol[i] += charges[i]*tau[i]

        pol = pol/volume # in e/bohr2
        pols_by_layer.append(unit_conversion(pol))

    return pols_by_layer

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def column_polarization(config, born_charges):

    """

    Calculates supercell polarization in the current configuration
    in vertical (z-axis) columns using the given effective charges.

    Parameters:
    ----------
    - born_charges (dict): dictionary with element labels as keys
    and effective charge 3D vectors as values. (in elemental charge units)

    Return:
    ----------
    - a 2D numpy array of 3D vectors with the macroscopic polarization (in C/m2)
    
    """

    if not isinstance(config, MCConfiguration):
        raise ezSCUP.exceptions.InvalidMCConfiguration

    labels = list(born_charges.keys())

    for l in labels:
        if l not in config.geo.elements:
            raise ezSCUP.exceptions.InvalidLabel

    
    cnts = config.geo.lat_constants
    stra = config.geo.strains
    ncells_per_column = config.geo.supercell[2]

    ucell_volume = (cnts[0]*(1+stra[0]))*(cnts[1]*(1+stra[1]))*(cnts[2]*(1+stra[2]))
    volume = ucell_volume*ncells_per_column


    pols_by_column = np.zeros((config.geo.supercell[0], config.geo.supercell[1]))
    for x in range(config.geo.supercell[0]):
            for y in range(config.geo.supercell[1]):

                pol = np.zeros(3)
                for z in range(config.geo.supercell[2]):

                    for label in config.geo.elements:

                        tau = config.geo.cells[x,y,z].displacements[label]
                        charges = born_charges[label]
                        
                        for i in range(3):
                            pol[i] += charges[i]*tau[i]


                pol = pol/volume # in e/bohr2
                pols_by_column[x,y] = unit_conversion(pol)

    return pols_by_column
'''