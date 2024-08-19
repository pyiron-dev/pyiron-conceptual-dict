import datetime
from pybis import Openbis
from getpass import getpass
import json

class OpenBIS:
    def __init__(self, instance, mappings_path): #TODO: mappings path sort out

        self.instance = instance
        self.read_map_file(instance, mappings_path)
        
        self.o = Openbis(self.url, verify_certificates=False)
        self.space = None
        self.project = None
        self.collection = None
        self.login()

    def read_map_file(self, instance, mappings_path):
        loc = mappings_path + '/mappings.json'
        with open(loc) as f:
            ob = json.load(f)['openbis']
            try:
                self.url = ob[instance]['url']
                self.username = ob[instance]['username']
                try:
                    self.dataset_type = ob[instance]['dataset_type']
                except KeyError:
                    self.dataset_type = 'RAW_DATA'
                mapping_f = 'rdm_mappings/' + ob[instance]['mapping']
                with open(mapping_f) as m:
                    self.mapping = json.load(m) #TODO add checks for file existence, resulting dicttype
            except KeyError:
                print(f"Mapping info for the '{instance}' OpenBIS instance is not present in the mappings file {mappings_path}.")

    def login(self):
        self.o.login(self.username, getpass('Enter openBIS password: '))

    def logout(self):
        self.o.logout()

    def get_space(self, openbis_space=None):
        if not self.o.is_session_active():
            self.login()
        if not openbis_space:
            openbis_space = self.username
        self.space = self.o.get_space(openbis_space)

    def get_project(self, openbis_project):
        if not self.space:
            self.get_space()
        try:
            self.project = self.space.get_project(openbis_project)
        except ValueError:
            self.project = self.o.new_project(space=self.space.code, code=openbis_project, 
                               description='Project for pyiron calculations created on {}'.format(datetime.datetime.today()))
            self.project.save()

    def get_collection(self, openbis_collection, coll_type='collection'):    # Collection types are only collection & default_experiment as far as I know
        if not self.project:
            self.get_project('project')                                      # TODO: reasonable default/take first - self.space.get_projects()[0] / else

        self.collection = self.o.get_collections(openbis_collection, project=self.project.code)[0]
        if not self.collection:                                              # Now defaults collection name to pyiron project name
            self.collection = self.o.new_collection(code=openbis_collection, type=coll_type, project=self.project.code)
            self.collection.save()

    def flatten_cdict(self, cdict):
        flat = {}
        for k, v in cdict.items():
            if k != '@context':
                if isinstance(v, dict):
                    if 'label' in v.keys():
                        flat[k] = v['label']
                    else:
                        flat = flat | self.flatten_cdict(v)
                elif k == 'inputs' or k == 'outputs':
                    for i in v:
                        flat[i['label']] = i['value']
                elif k == 'software':
                    flat[k] = v[0]['label']
                else:
                    flat[k] = v
        return flat
        
    def map_cdict(self, cdict):
        m = self.mapping[cdict['job_type']] # TODO also use flattened?
        ob_dict = {}

        cdict_used = self.flatten_cdict(cdict)
        
        for k, v in cdict_used.items():
            if k in m.keys():
                if 'terms' in m[k].keys():
                    ob_dict[m[k]['openbis_code'].lower()] = m[k]['terms'][v]
                else:
                    ob_dict[m[k]['openbis_code'].lower()] = v
    
        return ob_dict

    def upload_job(self, cdict, openbis_project=None, openbis_collection=None):
        if openbis_project:
            self.get_project(openbis_project)
        if openbis_collection:
            self.get_collection(openbis_collection)
        elif not self.collection:
            self.get_collection(cdict['project_name'])

        object_type = self.mapping[cdict['job_type']]['object_type']
        
        obj = self.collection.get_objects(code=cdict['job_name'])[0]
        if obj:
            print('Cannot upload - this job already exists in OpenBIS.')
        else:
            obj = self.o.new_object(code=cdict['job_name'], project=self.project, collection=self.collection, type=object_type)

            obj.props['$name'] = cdict['job_name']
            obj.props = self.map_cdict(cdict)
            obj.save()
    
            path_to_h5 = cdict['project_name'] + '/' + str(cdict['job_name']) + '.h5'    # Could use PATH from cdict but need relative...
            dataset = self.o.new_dataset(type=self.dataset_type, collection=self.collection, object=obj, files=[path_to_h5], props={'$name':cdict['job_name']+'.h5'})
            dataset.save()

    # ----------------------------------------------------------------------------------------------------------------------------------------

    def download_job(self):
        pass

    def reload_job(self):
        pass