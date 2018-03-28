"""
This is the class to handle all the DEIMOS specific attributes
DEIMOS specific DR techniques can be added to it in the future

12/14/2017 M. Brown - Created initial file
"""

import instrument
import datetime as dt

class Deimos(instrument.Instrument):
    def __init__(self, endTime=dt.datetime.now(), rDir=''):
        # Call the parent init to get all the shared variables
        super().__init__(endTime, rDir)

        """
        Values to be overwritten from Superclass
        """
        # Set the deimos specific paths to anc and stage
        seq = (self.rootDir,'/DEIMOS/', self.utDate, '/anc')
        self.ancDir = ''.join(seq)
        seq = (self.rootDir, '/stage')
        self.stageDir = ''.join(seq)
        # Generate the paths to the DEIMOS datadisk accounts
        self.paths = self.get_dir_list()

        """
        Values not included in superclass, specific to DEIMOS
        """
        # add the FCSIMGFI config file for deimos
        self.fcsimgfi = 'FCSIMGFI'


    def get_dir_list(self):
        """
        Function to generate the paths to all the DEIMOS accounts, including engineering
        Returns the list of paths
        """
        dirs = []
        path = '/s/sdata100'
        for i in range(1,4):
            seq = (path, str(i))
            path2 = ''.join(seq)
            for j in range(1,21):
                seq = (path2, '/deimos', str(j))
                path3 = ''.join(seq)
                dirs.append(path3)
            seq = (path2, 'dmoseng')
            dirs.append(''.join(seq))
        return dirs

    def set_prefix(self, keys):
        self.instr = self.set_instr(keys)
        if '/fcs' in keys[self.outdir]:
            prefix = 'DF'
        elif self.instr == 'deimos':
            prefix = 'DE'
        else:
            prefix = ''
        return prefix
