'''
This is the class to handle all the ESI specific attributes
ESI specific DR techniques can be added to it in the future

12/14/2017 M. Brown - Created initial file
'''

import instrument
import datetime as dt
from common import *
import numpy as np


class Esi(instrument.Instrument):

    def __init__(self, instr, utDate, rootDir, log=None):

        # Call the parent init to get all the shared variables
        super().__init__(instr, utDate, rootDir, log)


        # Set any unique keyword index values here
        self.keywordMap['UTC']       = 'UT'        


        # Other vars that subclass can overwrite
        #TODO: Ack! Looks like the old DEP has an hour difference between this value and the actual cron time!
        self.endTime = '20:00:00'   # 24 hour period start/end time (UT)


        # Generate the paths to the NIRES datadisk accounts
        self.sdataList = self.get_dir_list()


    def run_dqa_checks(self, progData):
        '''
        Run all DQA checks unique to this instrument.
        '''

        #todo: check that all of these do not need a subclass version if base class func was used.
        ok = True
        if ok: ok = self.set_instr()
        if ok: ok = self.set_dateObs()
        if ok: ok = self.set_utc()
        self.get_dispmode(update=True)
        self.get_camera(update=True)
        if ok: ok = self.set_instrume_esi(self)
        if ok: ok = self.set_koaimtyp()
        if ok: ok = self.set_koaid()
        if ok: ok = self.set_ut()
        if ok: ok = self.set_frameno()
        if ok: ok = self.set_esiofName()
        if ok: ok = self.set_semester()
        if ok: ok = self.set_prog_info(progData)
        if ok: ok = self.set_propint(progData)
        if ok: ok = self.set_datlevel(0)
        if ok: ok = self.set_image_stats_keywords()
        if ok: ok = self.set_weather_keywords()
        if ok: ok = self.set_oa()
        if ok: ok = self.set_npixsat(65535)

        if ok: ok = self.set_wavelengths()
        if ok: ok = self.set_slit_dims()
        if ok: ok = self.set_spatscal()
        if ok: ok = self.set_dispscal()
        if ok: ok = self.set_specres()
        if ok: ok = self.set_dqa_vers()
        if ok: ok = self.set_dqa_date()
        return ok


    @staticmethod
    def set_instrume_esi(self):
        instr = self.get_keyword("INSTRUME")
        if "ESI" in instr:
            self.set_keyword('INSTRUME','ESI','KOA: Instrument')
        return True

    def get_dir_list(self):
        '''
        Function to generate the paths to all the ESI accounts, including engineering
        Returns the list of paths
        '''
        dirs = []
        path = '/s/sdata70'
        for i in range(8):
            if i != 5:
                path2 = path + str(i) + '/esi'
                for j in range(1,21):
                    path3 = path2 + str(j)
                    dirs.append(path3)
                path3 = path2 + 'eng'
                dirs.append(path3)
        return dirs


    def get_prefix(self):

        instr = self.get_instr()
        if instr == 'esi': prefix = 'EI'
        else             : prefix = ''
        return prefix


    def set_koaimtyp(self):
        """
        Uses get_koaimtyp to set KOAIMTYP
        """

        #self.log.info('set_koaimtyp: setting KOAIMTYP keyword value')

        koaimtyp = self.get_koaimtyp()

        # Warn if undefined
        if koaimtyp == 'undefined':
            self.log.info('set_koaimtyp: Could not determine KOAIMTYP value')

        # Update keyword
        self.set_keyword('KOAIMTYP', koaimtyp, 'KOA: Image type')

        return True

    def set_esiofName(self):
        '''
        Sets OFNAME keyword from OUTFILE and FRAMENO
        '''

        outfile = self.get_keyword('OUTFILE', False)
        frameno = self.get_keyword('FRAMENO', False)
        if outfile == None or frameno == None:
            self.log.info('set_ofName: Could not detrermine OFNAME')
            ofname = ''
            return False
    
        frameno = str(frameno).zfill(4)
        ofName = ''.join((outfile, frameno, '.fits'))
        self.log.info('set_ofName: OFNAME = {}'.format(ofName))
        self.set_keyword('OFNAME', ofName, 'KOA: Original file name')

        return True


    def get_dispmode(self, update=False):
        """
        Determines spectrograph dispersion mode (low, high, null)
        """

        dispmode = self.get_keyword('DISPMODE')
        if dispmode == None:
            imfltnam = self.get_keyword('IMFLTNAM', default='').lower()
            ldfltnam = self.get_keyword('LDFLTNAM', default='').lower()
            prismnam = self.get_keyword('PRISMNAM', default='').lower()

            if   imfltnam == 'out' and ldfltnam == 'in'  and prismnam == 'in' : dispmode = 'low'
            elif imfltnam == 'out' and ldfltnam == 'out' and prismnam == 'in' : dispmode = 'high'
            elif imfltnam == 'in'  and ldfltnam == 'out' and prismnam == 'out': dispmode = 'null'

            if update: self.set_keyword('DISPMODE', dispmode, 'KOA: Spectrograph dispersion mode')

        return dispmode


    def get_camera(self, update=False):
        '''
        Determines instrument camera mode (imag or spec)
        '''
        camera = self.get_keyword('CAMERA')
        if camera == None:
            dispmode = self.get_dispmode()
            if dispmode in ('low', 'high'): camera = 'spec'
            else                          : camera = 'imag'

            if update: self.set_keyword('CAMERA', camera, 'KOA: Instrument camera mode')

        return camera


    def get_koaimtyp(self):
        """
        Determine image type based on instrument keyword configuration
        """

        # Default KOAIMTYP value
        koaimtyp = 'undefined'

        # Check OBSTYPE first
        obstype = self.get_keyword('OBSTYPE').lower()

        if obstype == 'bias': return 'bias'
        if obstype == 'dark': return 'dark'

        slmsknam = self.get_keyword('SLMSKNAM').lower()
        hatchpos = self.get_keyword('HATCHPOS').lower()
        lampqtz1 = self.get_keyword('LAMPQTZ1').lower()
        lampar1 = self.get_keyword('LAMPAR1').lower()
        lampcu1 = self.get_keyword('LAMPCU1').lower()
        lampne1 = self.get_keyword('LAMPNE1').lower()
        lampne2 = self.get_keyword('LAMPNE2').lower()
        prismnam = self.get_keyword('PRISMNAM').lower()
        imfltnam = self.get_keyword('IMFLTNAM').lower()
        axestat = self.get_keyword('AXESTAT').lower()
        domestat = self.get_keyword('DOMESTAT').lower()
        el = self.get_keyword('EL')
        dwfilnam = self.get_keyword('DWFILNAM').lower()

        # Hatch
        hatchOpen = 1
        if hatchpos == 'closed': hatchOpen = 0

        # Is flat lamp on?
        flat = 0
        if lampqtz1 == 'on': flat = 1

        # Is telescope pointed at flat screen?
        flatPos = 0
        if el >= 44.0 and el <= 46.01: flatPos = 1

        # Is an arc lamp on?
        arc = 0
        if lampar1 == 'on' or lampcu1 == 'on' or lampne1 == 'on' or lampne2 == 'on':
            arc = 1

        # Dome/Axes tracking
        axeTracking = domeTracking = 0
        if axestat == 'tracking': axeTracking = 1
        if domestat == 'tracking': domeTracking = 1

        # This is a trace or focus
        if 'hole' in slmsknam:
            if not hatchOpen:
                if flat and not arc and prismnam == 'in' and imfltnam == 'out': 
                    return 'trace'
                if flat and not arc and prismnam != 'in' and imfltnam != 'out': 
                    return 'focus'
                if not flat and arc and prismnam == 'in' and imfltnam == 'out': 
                    return 'focus'
            else:
                if prismnam == 'in' and imfltnam == 'out':
                    if obstype == 'dmflat' and not domeTracking and flatPos: 
                        return 'trace'
                    if not axeTracking and not domeTracking and flatPos: 
                        return 'trace'
                    if obstype == 'dmflat' and not axeTracking and not domeTracking and flatPos: 
                        return 'trace'
                    if obstype == 'dmflat' and not axeTracking and flatPos: 
                        return 'trace'
                else:
                    if obstype == 'dmflat' and not domeTracking and flatPos: 
                        return 'focus'
                    if not axeTracking and not domeTracking and flatPos: 
                        return 'focus'
                    if obstype == 'dmflat' and not axeTracking and not domeTracking and flatPos: 
                        return 'focus'
                    if obstype == 'dmflat' and not axeTracking and flatPos: 
                        return 'focus'
            try:
                idfltnam = self.get_keyword('IDFLTNAM').lower()
                if prismnam == 'out' and infltnam == 'in' and idfltnam == 'out': 
                    return 'focus'
                if prismnam == 'in' and infltnam == 'out' and dwfilnam == 'clear_s': 
                    return 'focus'
            except:
                pass
        #if not hole in slmsknam
        else:
            #if hatch closed
            if not hatchOpen:
                if flat and not arc: 
                    return 'flatlamp'
                if not flat and arc and prismnam == 'in' and imfltnam == 'out': 
                    return 'arclamp'
            #if hatch open
            else:
                if obstype == 'dmflat' and not domeTracking and flatPos: 
                    return 'flatlamp'
                if not axeTracking and not domeTracking and flatPos: 
                    return 'flatlamp'
                if obstype == 'dmflat' and not axeTracking and not domeTracking: 
                    return 'flatlamp'
                if obstype == 'dmflat' and not axeTracking and flatPos: 
                    return 'flatlamp'
                if not flat and not arc: 
                    return 'object'

        return 'undefined'


    def set_wavelengths(self):
        '''
        Adds wavelength keywords.
        '''

        # self.log.info('set_wavelengths: setting wavelength keyword values')

        #todo: verify these values below
        camera  = self.get_camera()

        #imaging:
        if (camera == 'imag'):
            #esifilter = self.get_keyword('TVFILNAM')
            esifilter = self.get_keyword('DWFILNAM')
            if esifilter == 'B':
                self.set_keyword('WAVERED' , 5400, 'KOA: Red end wavelength')
                self.set_keyword('WAVECNTR', 4400, 'KOA: Center wavelength')
                self.set_keyword('WAVEBLUE', 3700, 'KOA: Blue end wavelength')
            elif esifilter == 'V':
                self.set_keyword('WAVERED' , 6450, 'KOA: Red end wavelength')  
                self.set_keyword('WAVECNTR', 5200, 'KOA: Center wavelength')
                self.set_keyword('WAVEBLUE', 4900, 'KOA: Blue end wavelength')
            elif esifilter == 'R':
                self.set_keyword('WAVERED' , 7400, 'KOA: Red end wavelength')  
                self.set_keyword('WAVECNTR', 6500, 'KOA: Center wavelength')
                self.set_keyword('WAVEBLUE', 6000, 'KOA: Blue end wavelength')
            elif esifilter == 'I':
                self.set_keyword('WAVERED' , 9000, 'KOA: Red end wavelength')
                self.set_keyword('WAVECNTR', 8000, 'KOA: Center wavelength')
                self.set_keyword('WAVEBLUE', 7000, 'KOA: Blue end wavelength')

        #spec:
        elif (camera == 'spec'):
            self.set_keyword('WAVERED' , 10900, 'KOA: Red end wavelength')
            self.set_keyword('WAVECNTR',  7400, 'KOA: Center wavelength')
            self.set_keyword('WAVEBLUE',  3900, 'KOA: Blue end wavelength')

        return True


    def set_specres(self):
        '''
        Adds nominal spectral resolution keyword
        '''

        # self.log.info('set_specres: setting SPECRES keyword values')

        camera   = self.get_camera()
        if (camera == 'spec'):
            #spectral resolution R found over all wavelengths and dispersions between orders 6-15
            #
            #           wavelength           0.1542[arcsec/pixel] * wavelength[angstroms]
            # R    =   -----------     =    ---------------------------------------------
            #         deltawavelength       slitwidth[arcsec] * dispersion[angstroms/pixel]
            # 
            #           MEAN(0.1542*wavelength/dispersion)         4125.406
            # R    =    -----------------------------------   =   -----------
            #                       slitwidth                      slitwidth
            #
            #from echellette table https://www.keck.hawaii.edu/realpublic/inst/esi/Sensitivities.html
            specres = 4125.406/self.get_keyword('SLITWIDT')
            specres = np.round(specres,-1)
            self.set_keyword('SPECRES' , specres,  'KOA: Nominal spectral resolution')
        return True


    def set_dispscal(self):
        '''
        Adds CCD pixel scale, dispersion (arcsec/pixel) keyword to header.
        '''
        #set dispersion scale to 0.1542 for imaging and spectroscopy
        camera   = self.get_camera()
        dispscal = None
        if camera in ['imag','spec']: 
            dispscal = 0.1542 #arcsec/pixel
        self.set_keyword('DISPSCAL' , dispscal, 'KOA: CCD pixel scale, dispersion')
        return True


    def set_spatscal(self):
        '''
        Adds spatial scale keyword to header.
        '''
        #set spatial scale to 0.1542 for imaging and spectroscopy
        camera   = self.get_camera()
        spatscal = None
        if camera in ['imag','spec']: 
            spatscal = 0.1542 #arsec/pixel
        self.set_keyword('SPATSCAL' , spatscal, 'KOA: CCD pixel scale, spatial')
        return True


    def set_slit_dims(self):
        '''
        Adds slit length and width keywords to header.
        '''

        camera   = self.get_camera()
        dispmode = self.get_dispmode()

        #add keywords for 'spec' only
        if (camera == 'spec'):
            #set slitlength
            slitlen = None
            if   dispmode == 'low' : slitlen = 8*60 #8 arcminutes = 480 arcseconds
            elif dispmode == 'high': slitlen = 20 #20 arcseconds
            self.set_keyword('SLITLEN'  , slitlen,  'KOA: Slit length projected on sky')
            #set slitwidth
            slitwidt = None
            slmsknam = self.get_keyword('SLMSKNAM')
            print(slmsknam)
            if slmsknam:
                if slmsknam == 'MultiHoles':
                    slitwidt = 0.5
                else:
                    try:
                        slitwidt = float(slmsknam.split('_')[0])
                    except:
                        slitwidt = float(slmsknam.split('_')[1])
            self.set_keyword('SLITWIDT' , slitwidt, 'KOA: Slit width projected on sky')

        return True
