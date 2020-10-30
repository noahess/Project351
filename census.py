import geopandas as gpd
import pandas as pd
import numpy as np
import csv

import glob
import us


class TableShell:
    def __init__(self, table_id, sequence, start_position, num_cells, title, column_titles, column_indexes, specs):
        self.id = table_id
        self.sequence = sequence
        self.start_position = start_position
        self.start = self.start_position
        self.num_cells = num_cells
        self.title = title
        self.column_indexes_relative = column_indexes
        self.column_titles = column_titles
        self.column_names = self.column_titles
        self.column_indexes = column_indexes + self.start - 2
        self.specs = specs
        

class Table:
    def __init__(self, table_spec: TableShell, sequence_data: pd.DataFrame, geoid_match=None):
        self.spec = table_spec
        self.geoid_match = geoid_match
        
        self.data = sequence_data[table_spec.column_indexes]
        self.data.columns = self.spec.column_names
        self.data.insert(0, 'LOGRECNO', sequence_data[5])
        
        if geoid_match is not None:
            self.data = self.data.merge(geoid_match, on='LOGRECNO').drop(columns='LOGRECNO')

            
class GeoTable(Table):
    def __init__(self, table_spec: TableShell, sequence_data: pd.DataFrame, geoid_match: pd.DataFrame, geo_frame: gpd.GeoDataFrame):
        super().__init__(table_spec, sequence_data, geoid_match)
        
        self.data = geo_frame.merge(self.data, left_on='GEOID', right_on='GEOID12')
            
        
class Lookup:
    def __init__(self):
        with open('ACS_5yr_Seq_Table_Number_Lookup.csv', 'r') as csv_file:
            self._rows = np.array([row for row in csv.reader(csv_file)])[1:]
    
    def get_table_spec(self, table_id: str) -> Table:
        data = self._rows[self._rows[:, 1] == table_id]
        t = TableShell(
            data[0, 1],
            int(data[0, 2]),
            int(data[0, 4]),
            int(data[0, 5].split(' ')[0]),
            data[0, 7],
            data[2:, 7],
            pd.to_numeric(data[2:, 3]),
            {
                "Universe": data[1, 7],
                "Family": data[0, 8]
            }
        )
        return t
    
    def __getattr__(self, attr: str) -> Table:
        return self.get_table(attr)
    
    @staticmethod
    def get_folder_name(state_name_or_fips: str) -> str:
        base_name = us.states.lookup(state_name_or_fips).name.replace(' ', '')
        return f"{base_name}_Tracts_Block_Groups_Only"    
    
    
class State(us.states.State):
    def __init__(self, state_name_or_fips: str, lookup_library: Lookup):
        my_data = us.states.lookup(state_name_or_fips).__dict__
        super().__init__(**my_data)
        
        self.lookup_library = lookup_library
        self.base_folder = self.lookup_library.get_folder_name(self.fips)
        
        file_name = glob.glob(self.base_folder + '/g20185*.csv')[0]
        self.locations = pd.read_csv(file_name, names=np.loadtxt('geo_file_template.csv', delimiter=',', dtype=object), engine='python')
        self.bgs = self._fix_blkgrp_geoid_issue()
        self.geo = self.load_geometry()
        
    def load_geometry(self):
        return gpd.read_file(f"zip:///Users/njsto/Downloads/BG/tl_2018_{self.fips}_bg.zip")
        
    def _fix_blkgrp_geoid_issue(self) -> pd.DataFrame:
        bgs = self.locations[self.locations['BLKGRP'].notna()]
        
        def conv_to_str(df: pd.DataFrame, padding: int):
            template_str = '{:0>' + str(padding) + 'd}'
            return np.array(list(map(lambda x: template_str.format(x), df.astype('int'))))

        geoid = conv_to_str(bgs['STATE'], 2)
        for col, pad in [['COUNTY', 3], ['TRACT', 6], ['BLKGRP', 1]]:
            geoid = np.char.add(geoid, conv_to_str(bgs[col], pad))
    
        bgs.insert(bgs.columns.get_loc('GEOID'), 'GEOID12', geoid)
    
        return bgs
    
    def get_sequence(self, sequence_num: int) -> pd.DataFrame:
        file_pattern = ('000' + str(sequence_num))[-4:] + '000.txt'
        match = glob.glob(f'{self.base_folder}/e20185*{file_pattern}')
        if len(match) != 1:
            raise Exception('Glob failed')
        return pd.read_csv(match[0], header=None, low_memory=False)

    def get_table(self, table_id: str) -> Table:
        spec = self.lookup_library.get_table_spec(table_id)
        return Table(spec, 
                        self.get_sequence(spec.sequence), 
                        self.bgs[['LOGRECNO', 'GEOID12', 'NAME', 'STATE', 'COUNTY', 'TRACT', 'BLKGRP']]
                       )
    
    def get_geo_table(self, table_id: str) -> Table:
        spec = self.lookup_library.get_table_spec(table_id)
        return GeoTable(spec, 
                        self.get_sequence(spec.sequence), 
                        self.bgs[['LOGRECNO', 'GEOID12', 'NAME', 'STATE', 'COUNTY', 'TRACT', 'BLKGRP']],
                        self.geo
                       )