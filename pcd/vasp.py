"""
VASP specific functions for parsing

Use this a reference for specific implementations
"""
import os
import numpy as np
import ast

def process_job(job):
    method_dict = {}
    add_contexts(method_dict)
    #get_structures(job, method_dict)
    identify_method(job, method_dict)
    extract_calculated_quantities(job, method_dict)
    add_software(method_dict)
    get_simulation_folder(job, method_dict)
    return method_dict

def add_contexts(method_dict):
    method_dict['@context'] = {}
    method_dict['@context']['sample'] = 'http://purls.helmholtz-metadaten.de/cmso/AtomicScaleSample'
    method_dict['@context']['path'] = 'http://purls.helmholtz-metadaten.de/cmso/hasPath'
    method_dict['@context']['dof'] = 'http://purls.helmholtz-metadaten.de/asmo/hasRelaxationDOF'
    method_dict['@context']['inputs'] = 'http://purls.helmholtz-metadaten.de/asmo/hasInputParameter'
    method_dict['@context']['label'] = 'http://www.w3.org/2000/01/rdf-schema#label'
    method_dict['@context']['unit'] = 'http://purls.helmholtz-metadaten.de/asmo/hasUnit'
    method_dict['@context']['value'] = 'http://purls.helmholtz-metadaten.de/asmo/hasValue'
    method_dict['@context']['outputs'] = 'http://purls.helmholtz-metadaten.de/cmso/hasCalculatedProperty'
    #method_dict['@context']['workflow_manager'] = ''
    #method_dict['@context']['software'] = ''
    method_dict['@context']['dft'] = "http://purls.helmholtz-metadaten.de/asmo/DensityFunctionalTheory"
    method_dict['@context']['xc_functional'] = 'https://w3id.org/mdo/calculation/hasXCFunctional'

def get_simulation_folder(job, method_dict):
    method_dict['path'] = os.path.join(job.project.path, f'{job.name}_hdf5')

def get_structures(job, method_dict):
    initial_pyiron_structure = job.structure
    final_pyiron_structure = job.get_structure(frame=-1)
    
    method_dict['sample'] =  {'initial':initial_pyiron_structure, 
                            'final': final_pyiron_structure}
    
def identify_method(job, method_dict):
    indf = job.input.incar.to_dict()
    params = indf['data_dict']['Parameter']
    vals = indf['data_dict']['Value']
    mlist = []
    for p,v in zip(params, vals):
        mlist.append(p + '=' + v)
    mstring = ';'.join(mlist)
    raw = mstring.split(';')
    mdict = {}
    for r in raw:
        rsplit = r.split('=')
        if len(rsplit) == 2:
            mdict[rsplit[0].replace(' ','')] = rsplit[1].replace(' ','')
    dof = []
    if 'ISIF' in mdict.keys():
        if mdict['ISIF'] in ['0', '1', '2']:
            dof.append('AtomicPositionRelaxation')
        elif mdict['ISIF'] == '3':
            dof.append('AtomicPositionRelaxation')
            dof.append('CellShapeRelaxation')
            dof.append('CellVolumeRelaxation')
        elif mdict['ISIF'] == '4':
            dof.append('AtomicPositionRelaxation')
            dof.append('CellShapeRelaxation')
        elif mdict['ISIF'] == '5':
            dof.append('CellShapeRelaxation')
        elif mdict['ISIF'] == '6':
            dof.append('CellShapeRelaxation')
            dof.append('CellVolumeRelaxation')
        elif mdict['ISIF'] == '7':
            dof.append('CellVolumeRelaxation')
        elif mdict['ISIF'] == '8':
            dof.append('AtomicPositionRelaxation')
            dof.append('CellVolumeRelaxation')
    if 'NSW' in mdict.keys():
        if mdict['NSW'] == '0':
            dof = []

    method_dict['dft'] = {}
    method_dict['dof'] = dof

    method_dict['dft']['inputs'] = []

    encut_dict = {}
    encut_dict['value'] = mdict['ENCUT']
    encut_dict['label'] = 'energy_cutoff'
    encut_dict['unit'] = 'eV'
    method_dict['dft']['inputs'].append(encut_dict)

    indf = job.input.to_dict()['kpoints/data_dict']
    params = indf['Parameter']
    vals = indf['Value']   

    kpoint_type = vals[2]
    kpoint_grid = vals[3]

    kpoint_dict = {}
    kpoint_dict['label'] = f'kpoint_{kpoint_type}'
    kpoint_dict['value'] = kpoint_grid
    method_dict['dft']['inputs'].append(kpoint_dict)

    indf = job.input.to_dict()['potcar/data_dict']
    xc = indf['Value'][0]
    method_dict['xc_functional'] = xc

def add_software(method_dict):
    method_dict["workflow_manager"] = {}
    method_dict["workflow_manager"]["@id"] = "http://demo.fiz-karlsruhe.de/matwerk/E457491"
    method_dict["workflow_manager"]["label"] = "pyiron"
    # and finally code details

    software = {
        "@id": "https://www.vasp.at/",
        "label": "VASP",
    }
    method_dict["software"] = [software]

def extract_calculated_quantities(job, method_dict):
    """
    Extracts calculated quantities from a job.

    Parameters
    ----------
    job : pyiron.Job
        The job object containing the calculated quantities.

    Returns
    -------
    list
        A list of dictionaries, each containing the label, value, unit, and associate_to_sample of a calculated quantity.

    """
    outputs = []
    outputs.append(
        {
            "label": "TotalEnergy",
            "value": np.round(job.output.energy_tot[-1], decimals=5),
            "unit": "EV",
            "associate_to_sample": True,
        }
    )
    outputs.append(
        {
            "label": "TotalVolume",
            "value": np.round(job.output.volume[-1], decimals=5),
            "unit": "ANGSTROM3",
            "associate_to_sample": True,
        }
    )

    method_dict['outputs'] =  outputs    