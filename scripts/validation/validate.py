"""A script to compare this frameworks AM1BCC implementation with the
built-in OpenEye implementation."""
import json
import logging
import warnings
from multiprocessing import Pool
from pprint import pprint
from typing import Dict, List, Tuple

from openeye import oechem
from tqdm import tqdm

from openff.recharge.charges.bcc import (
    BCCGenerator,
    compare_openeye_parity,
    original_am1bcc_corrections,
)
from openff.recharge.charges.exceptions import ChargeAssignmentError
from openff.recharge.conformers.exceptions import ConformerGenerationError
from openff.recharge.utilities.molecule import smiles_to_molecule

warnings.filterwarnings("ignore")
logging.getLogger("openff.toolkit").setLevel(logging.ERROR)

N_PROCESSES = 1

output_stream = oechem.oeosstream()

oechem.OEThrow.SetOutputStream(output_stream)
oechem.OEThrow.Clear()


def load_molecule(smiles: str) -> Tuple[bool, List[str]]:
    """Filters out molecules which should not be included in the
    validation set. This include molecules which contain elements
    which the bond charge corrections don't cover, over molecules
    which would be to heavily to validate against swiftly.

    Parameters
    ----------
    smiles
        The SMILES pattern to apply the filter to.

    Returns
    -------
        Whether to include the molecule or not.
    """

    try:
        molecule = smiles_to_molecule(smiles, guess_stereochemistry=True)

        allowed_elements = [1, 6, 7, 8, 9, 15, 16, 17, 35]

        if not all(atom.atomic_number in allowed_elements for atom in molecule.atoms):
            return False, []

        corrections = BCCGenerator.applied_corrections(
            smiles_to_molecule(smiles, guess_stereochemistry=True),
            bcc_collection=original_am1bcc_corrections(),
        )

        return True, [bcc.provenance["code"] for bcc in corrections]

    except BaseException:  # lgtm [py/catch-base-exception]
        return False, []


def load_molecules() -> Dict[str, List[str]]:
    print("Loading molecules...")

    with oechem.oemolistream("validation-set.smi") as input_stream:
        smiles = [
            oechem.OECreateIsoSmiString(oe_molecule)
            for oe_molecule in input_stream.GetOEMols()
        ]

    with Pool(processes=N_PROCESSES) as pool:
        molecule_generator = tqdm(pool.imap(load_molecule, smiles), desc="filtering")

        smiles = {
            pattern: bcc_codes
            for pattern, (retain, bcc_codes) in zip(smiles, molecule_generator)
            if retain
        }

    return smiles


def validate_molecule(smiles: str) -> Tuple[str, bool, bool]:
    tqdm.write(smiles)

    molecule = smiles_to_molecule(smiles, guess_stereochemistry=True)

    try:
        identical_charges = compare_openeye_parity(molecule)
    except ConformerGenerationError:
        tqdm.write(f"could not generate conformers for {smiles}")
        return smiles, True, False
    except ChargeAssignmentError:
        tqdm.write(f"could not generate charges for {smiles}")
        return smiles, True, False
    except BaseException:  # lgtm [py/catch-base-exception]
        tqdm.write(f"unexpected error for {smiles}")
        return smiles, True, False

    tqdm.write("passed" if identical_charges else "failed")
    return smiles, False, identical_charges


def main():
    # # Construct a list of molecule from both the NCI 2012 Open set and
    # # a list of hand curated SMILES patterns chosen to exercise the more
    # # uncommon bond charge correction parameters, and determine which
    # # bond charge corrections they exercise.
    # if not os.path.isfile("validation-molecules.json"):
    #
    #     coverage_smiles = load_molecules()
    #
    #     with open("validation-molecules.json", "w") as file:
    #         json.dump(coverage_smiles, file)

    with open("validation-molecules.json") as file:
        coverage_smiles = json.load(file)

    # # Check which bond charge correction parameters weren't covered by the set.
    # all_bcc_codes = {
    #     bcc.provenance["code"] for bcc in original_am1bcc_corrections().parameters
    # }
    # covered_codes = {
    #     bcc_code
    #     for bcc_code_list in coverage_smiles.values()
    #     for bcc_code in bcc_code_list
    # }
    #
    # missed_codes = all_bcc_codes - covered_codes
    # print(f"Codes without coverage: {missed_codes}")
    #
    # # Select molecules from the above curated list and check whether the
    # # charges generated by this framework match the OpenEye implementation.
    # passed_smiles = set()
    # failed_smiles = set()
    #
    # with Pool(processes=N_PROCESSES) as pool:
    #
    #     for smiles, should_skip, identical_charges in tqdm(
    #         pool.imap(validate_molecule, coverage_smiles),
    #         desc="validating...",
    #         total=len(coverage_smiles)
    #     ):
    #
    #         if should_skip:
    #             continue
    #
    #         if identical_charges:
    #             passed_smiles.add(smiles)
    #         else:
    #             failed_smiles.add(smiles)
    #
    # with open("passed-smiles.json", "w") as file:
    #     json.dump([*passed_smiles], file)
    # with open("failed-smiles.json", "w") as file:
    #     json.dump([*failed_smiles], file)

    with open("failed-smiles.json") as file:
        failed_smiles = json.load(file)

    failed_codes = {
        code for smiles in failed_smiles for code in coverage_smiles[smiles]
    }

    pprint(failed_codes)

    validate_molecule("N[O-]")


if __name__ == "__main__":
    main()
