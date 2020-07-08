import itertools
from typing import TYPE_CHECKING

import numpy
from openeye import oechem
from pydantic import BaseModel, Field
from typing_extensions import Literal

if TYPE_CHECKING:
    PositiveFloat = float
else:
    from pydantic import PositiveFloat


class GridSettings(BaseModel):
    """A class which encodes the settings to use when generating a
    grid to compute the electrostatic potential of a molecule on."""

    type: Literal["fcc"] = Field("fcc", description="The type of grid to generate.")

    spacing: PositiveFloat = Field(
        0.5, description="The grid spacing in units of angstroms."
    )

    inner_vdw_scale: PositiveFloat = Field(
        1.4,
        description="A scalar which defines the inner radius of the shell "
        "around the molecule to retain grid points within.",
    )
    outer_vdw_scale: PositiveFloat = Field(
        2.0,
        description="A scalar which defines the outer radius of the shell "
        "around the molecule to retain grid points within.",
    )


class GridGenerator:
    """A containing methods to generate the grids upon which the
    electrostatic potential of a molecule will be computed."""

    @classmethod
    def generate(
        cls, oe_molecule: oechem.OEMol, conformer: numpy.ndarray, settings: GridSettings
    ) -> numpy.ndarray:
        """Generates a grid of points in a shell around a specified
        molecule in a given conformer according a set of settings.

        Parameters
        ----------
        oe_molecule
            The molecule to generate the grid around.
        conformer
            The conformer of the molecule with shape=(n_atoms, 3).
        settings
            The settings which describe how the grid should
            be generated.

        Returns
        -------
            The coordinates of the grid with shape=(n_grid_points, 3).
        """

        # Only operate on a copy of the molecule.
        oe_molecule = oechem.OEMol(oe_molecule)
        # Assign a radius to each atom in the molecule.
        oechem.OEAssignBondiVdWRadii(oe_molecule)

        # Store the radii in a numpy array.
        oe_atoms = {atom.GetIdx(): atom for atom in oe_molecule.GetAtoms()}

        radii = numpy.array(
            [[oe_atoms[index].GetRadius()] for index in range(oe_molecule.NumAtoms())]
        )

        # Compute the center of the molecule
        conformer_center = numpy.mean(conformer, axis=0)

        # Compute the bounding box which the grid should roughly fit inside of.
        minimum_bounds = numpy.min(conformer - radii * settings.outer_vdw_scale, axis=0)
        maximum_bounds = numpy.max(conformer + radii * settings.outer_vdw_scale, axis=0)

        n_cells = int(
            numpy.ceil(numpy.max(maximum_bounds - minimum_bounds) / settings.spacing)
        )

        # Compute the coordinates of the
        coordinates = []

        for x, y, z in itertools.product(range(0, n_cells * 2 + 1), repeat=3):

            a = x % 2
            b = y % 2
            c = z % 2

            is_grid_point = (
                (not a and not b and not c)
                or (a and b and not c)
                or (not a and b and c)
                or (a and not b and c)
            )

            if not is_grid_point:
                continue

            coordinate = (
                numpy.array([[x - n_cells, y - n_cells, z - n_cells]])
                * 0.5
                * settings.spacing
                + conformer_center
            )

            # Determine the distance between the grid point and each atom in the
            # molecule.
            distances = numpy.sqrt(
                numpy.sum((coordinate - conformer) ** 2, axis=1)
            ).reshape(-1, 1)

            # # Check if the coordinate is inside the inner shell
            if numpy.any(distances < radii * settings.inner_vdw_scale):
                continue

            # Check if the coordinate is outside the outer shell
            if numpy.all(distances > radii * settings.outer_vdw_scale):
                continue

            coordinates.append(coordinate)

        return numpy.concatenate(coordinates)
