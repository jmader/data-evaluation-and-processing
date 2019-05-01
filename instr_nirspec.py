'''
This is the class to handle all the NIRSPEC specific attributes
NIRSPEC specific DR techniques can be added to it in the future

12/14/2017 M. Brown - Created initial file
'''

import instrument
import datetime as dt
from common import *

class Nirspec(instrument.Instrument):

    def __init__(self, instr, utDate, rootDir, log=None):

        #call the parent init to get all the shared variables
        super().__init__(instr, utDate, rootDir, log)

        #set any unique keyword index values here
        self.keywordMap['OFNAME'] = 'DATAFILE'
        self.keywordMap['FRAMENO'] = 'FRAMENUM'

        #other vars that subclass can overwrite
        self.endTime = '19:00:00'   # 24 hour period start/end time (UT)

        #generate the paths to the NIRSPEC datadisk accounts
        self.sdataList = self.get_dir_list()


    def run_dqa_checks(self, progData):
        '''
        Run all DQA checks unique to this instrument
        '''

        ok = True
        if ok: ok = self.set_dqa_date()
        if ok: ok = self.set_dqa_vers()
        if ok: ok = self.set_datlevel(0)
        if ok: ok = self.set_instr()
        if ok: ok = self.set_dateObs()
        if ok: ok = self.set_elaptime()
        if ok: ok = self.set_koaimtyp()
        if ok: ok = self.set_koaid()
        if ok: ok = self.set_frameno()
        if ok: ok = self.set_ofName()
        if ok: ok = self.set_semester()
        if ok: ok = self.set_isao()
        if ok: ok = self.set_dispers()
        if ok: ok = self.set_slit_values()
        if ok: ok = self.set_wavelengths()
        if ok: ok = self.set_weather_keywords()
        if ok: ok = self.set_image_stats_keywords()
        if ok: ok = self.set_gain_and_readnoise()
        if ok: ok = self.set_npixsat(self.get_keyword('COADDS') * 25000)
        if ok: ok = self.set_oa()
        if ok: ok = self.set_prog_info(progData)
        if ok: ok = self.set_propint(progData)

        return ok


    def get_dir_list(self):
        '''
        Function to generate the paths to all the NIRSPEC accounts, including engineering
        Returns the list of paths
        '''
        dirs = []
        path = '/s/sdata60'
        for i in range(4):
            joinSeq = (path, str(i))
            path2 = ''.join(joinSeq)
            for j in range(1,10):
                joinSeq = (path2, '/nspec', str(j))
                path3 = ''.join(joinSeq)
                dirs.append(path3)
            joinSeq = (path2, '/nspeceng')
            path3 = ''.join(joinSeq)
            dirs.append(path3)
            joinSeq = (path2, 'nirspec')
            path3 = ''.join(joinSeq)
            dirs.append(path3)
        return dirs


    def get_prefix(self):

        # SCAM = NC, SPEC = NS
        instr = self.get_instr()
        if instr == 'nirspec' or instr == 'nirspao':
            try:
                camera = self.get_keyword('CAMERA').lower()
                if camera == None:
                    camera = self.get_keyword('OUTDIR').lower()
            except KeyError:
                prefix = ''
            else:
                if 'scam' in camera:
                    prefix = 'NC'
                elif 'spec' in camera:
                    prefix = 'NS'
                else:
                    prefix = ''
        else:
            prefix = ''
        return prefix


    def set_elaptime(self):
        '''
        Fixes missing ELAPTIME keyword
        '''

        self.log.info('set_elaptime: determining ELAPTIME from TRUITIME')

        #skip it it exists
        if self.get_keyword('ELAPTIME', False) != None: return True

        #get necessary keywords
        itime  = self.get_keyword('TRUITIME')
        coadds = self.get_keyword('COADDS')
        if (itime == None or coadds == None):
            self.log.error('set_elaptime: TRUITIME and COADDS values needed to set ELAPTIME')
            return False

        #update val
        elaptime = round(itime * coadds, 5)
        self.set_keyword('ELAPTIME', elaptime, 'KOA: Total integration time')

        return True


    def set_ofName(self):
        """
        Adds OFNAME keyword to header
        """

        #OFNAME was added as a native NIRSPEC keyword around 20190405
        if self.get_keyword('OFNAME', False) != None: return True

        self.log.info('set_ofName: setting OFNAME keyword value')

        #get value
        ofName = self.get_keyword('OFNAME')
        if (ofName == None):
            self.log.error('set_ofName: cannot find value for OFNAME')
            return False

        #add *.fits to output if it does not exist (to fix old files)
        if (ofName.endswith('.fits') == False) : ofName += '.fits'

        #update
        self.set_keyword('OFNAME', ofName, 'KOA: Original file name')
        return True


    def set_koaimtyp(self):
        '''
        Fixes missing KOAIMTYP keyword.
        This is derived from OBSTYPE keyword.
        '''

        self.log.info('set_koaimtyp: setting KOAIMTYP keyword value from OBSTYPE')

        #get obstype value
        obstype = self.get_keyword('OBSTYPE')

        #map to KOAIMTYP value
        koaimtyp = 'undefined'
        validValsMap = {
            'object'  : 'object',
            'standard': 'object',   #NOTE: old val
            'telluric': 'object',
            'bias'    : 'bias',
            'dark'    : 'dark',
            'domeflat': 'domeflat',
            'domearc' : 'domearc',
#            'astro'   : 'object',   #NOTE: old val
#            'star'    : 'object',   #NOTE: old val
#            'calib'   : 'undefined' #NOTE: old val
        }

        #first use OBSTYPE value
        if (obstype != None and obstype.lower() in validValsMap):
            koaimtyp = validValsMap[obstype.lower()]

        #use algorithm
        else:
            self.log.info('set_koaimtyp: setting KOAIMTYP keyword value from algorithm')

            calmpos = self.get_keyword('CALMPOS').lower()
            calppos = self.get_keyword('CALPPOS').lower()
            #calcpos doesn't exist in header
#            calcpos = self.get_keyword('CALCPOS').lower()
            xenon = self.get_keyword('XENON').lower()
            krypton = self.get_keyword('KRYPTON').lower()
            argon = self.get_keyword('ARGON').lower()
            neon = self.get_keyword('NEON').lower()
#flat doesn't exist
#            flat = self.get_keyword('FLAT')
            flimagin = self.get_keyword('FLIMAGIN').lower()
            flspectr = self.get_keyword('FLSPECTR').lower()
            flat = 0
            if flimagin == 'on' or flspectr == 'on':
                flat = 1

            #arclamp
            if argon == 'on' or krypton == 'on' or neon == 'on' or xenon == 'on':
                if calmpos == 'in' and calppos == 'out':
                    koaimtyp = 'arclamp'
                else:
                    koaimtyp = 'undefined'

            #flats
            elif flat != None:
                if flat == 0 and calmpos == 'in':
                    koaimtyp = 'flatlampoff'
                elif flat == 1 and calmpos == 'in' and calppos == 'out':
                    koaimtyp = 'flatlamp'
                else:
                    koaimtyp = 'undefined'

            #darks
            elif int(self.get_keyword('ITIME')) == 0:
                koaimtyp = 'bias'

            #object
            elif calmpos == 'out' and calppos == 'out' and calcpos == 'out':
                koaimtyp = 'object'

        #warn if undefined
        if (koaimtyp == 'undefined'):
            self.log.info('set_koaimtyp: Could not determine KOAIMTYP from OBSTYPE value of "' + obstype + '"')

        #update keyword
        self.set_keyword('KOAIMTYP', koaimtyp, 'KOA: Image type')
        return True


    def set_wavelengths(self):
        '''
        Sets WAVEBLUE, CNTR, RED based on FILTER value
        '''

        self.log.info('set_wavelengths: setting WAVE keyword values from FILTER')

        filters = {}
        filters['NIRSPEC-1'] = {'blue':0.9470, 'cntr':1.0340, 'red':1.1210}
        filters['NIRSPEC-2'] = {'blue':1.0890, 'cntr':1.1910, 'red':1.2930}
        filters['NIRSPEC-3'] = {'blue':1.1430, 'cntr':1.2590, 'red':1.3750}
        filters['NIRSPEC-4'] = {'blue':1.2410, 'cntr':1.4170, 'red':1.5930}
        filters['NIRSPEC-5'] = {'blue':1.4310, 'cntr':1.6195, 'red':1.8080}
        filters['NIRSPEC-6'] = {'blue':1.5580, 'cntr':1.9365, 'red':2.3150}
        filters['NIRSPEC-7'] = {'blue':1.8390, 'cntr':2.2345, 'red':2.6300}
        filters['Br-Gamma']  = {'blue':2.1550, 'cntr':2.1650, 'red':2.1750}
        filters['BR-GAMMA']  = {'blue':2.1550, 'cntr':2.1650, 'red':2.1750}
        filters['CO']        = {'blue':2.2810, 'cntr':2.2930, 'red':2.3050}
        filters['K-PRIME']   = {'blue':1.9500, 'cntr':2.1225, 'red':2.2950}
        filters['K']         = {'blue':1.9960, 'cntr':2.1890, 'red':2.3820}
        filters['L-PRIME']   = {'blue':3.4200, 'cntr':3.7700, 'red':4.1200}
        filters['M-PRIME']   = {'blue':4.5700, 'cntr':4.6900, 'red':4.8100}
        filters['KL']        = {'blue':2.1340, 'cntr':3.1810, 'red':4.2280}
        filters['HEI']       = {'blue':1.0776, 'cntr':1.0830, 'red':1.0884}
        filters['PA-BETA']   = {'blue':1.2757, 'cntr':1.2823, 'red':1.2888}
        filters['FEII']      = {'blue':1.6390, 'cntr':1.6465, 'red':1.6540}
        filters['H2']        = {'blue':2.1100, 'cntr':2.1195, 'red':2.1290}
        filters['M-WIDE']    = {'blue':4.4200, 'cntr':4.9750, 'red':5.5300}

        filter = self.get_keyword('FILTER')
        if filter == None: return True

        waveblue = wavecntr = wavered = 'null'
        for filt, waves in filters.items():
            if filt in filter.upper():
                waveblue = waves['blue']
                wavecntr = waves['cntr']
                wavered = waves['red']

        self.set_keyword('WAVEBLUE', waveblue, 'KOA: Approximate blue end wavelength (u)')
        self.set_keyword('WAVECNTR', wavecntr, 'KOA: Approximate central wavelength (u)')
        self.set_keyword('WAVERED', wavered, 'KOA: Approximate red end wavelength (u)')

        return True


    def set_isao(self):
        '''
        Sets the ISAO keyword value: NIRSPEC = no, NIRSPAO = yes 
        '''
        
        self.log.info('set_isao: setting ISAO keyword values from INSTRUME')

        isao = 'no'
        instrume = self.get_keyword('INSTRUME')
        if instrume == 'NIRSPAO':
            isao = 'yes'

        self.set_keyword('ISAO', isao, 'KOA: Is this NIRSPAO data?')

        return True


    def set_dispers(self):
        '''
        Sets DISPERS, DISPSCAL and SPATSCAL keyword values based on ECLPOS value
        '''

        dispers = 'null'
        dispscal = 'null'
        spatscal = 'null'

        if 'NC' in self.get_keyword('KOAID'):
            spatscal = 0.178

        else:
            self.log.info('set_dispers: setting DISPERS and DISPSCAL keyword values from ECHLPOS')

            echlpos = self.get_keyword('ECHLPOS')
            isao = self.get_keyword('ISAO')

            #these values are for NIRSPEC, different for for NIRSAO
            if echlpos == None: dispers = 'unknown'
            elif echlpos <= 100.0:
                dispers = 'high'
                dispscal = 0.144
                spatscal = 0.190
                if isao == 'yes': spatscal = 0.018
            else:
                dispers = 'low'
                dispscal = 0.190
                spatscal = 0.144
                if isao == 'yes': spatscal = 0.013

        #update keywords
        self.set_keyword('DISPERS', dispers, 'KOA: dispersion level')
        self.set_keyword('DISPSCAL', dispscal, 'KOA: pixel scale, dispersion (arcsec/pixel)')
        self.set_keyword('SPATSCAL', spatscal, 'KOA: pixel scale, spatial (arcsec/pixel)')

        return True


    def set_slit_values(self):
        '''
        Sets keyword values defining the slit dimensions
        '''

        slitlen = 'null'
        slitwidt = 'null'
        specres = 'null'

        #low resoltuion slitwidt:specres
        lowres = {'0.38':2500, '0.57':2000, '0.76':1800}
        #high resolution slitwidtAO:slitwidt
        highres = {}
        highres['0.0136'] = 0.144
        highres['0.0271'] = 0.288
        highres['0.0407'] = 0.432
        highres['0.0543'] = 0.576
        highres['0.0679'] = 0.720
        highres['0.0272'] = 0.288
        highres['0.0407'] = 0.432
        highres['0.0358'] = 0.380
        highres['0.0538'] = 0.570
        highres['0.0717'] = 0.760
        if self.prefix == 'NS':
            self.log.info('set_slit_values: setting SLITLEN and SLITWIDT keyword values from SLITNAME')
            slitname = self.get_keyword('SLITNAME')
            if 'x' in slitname:
                #SLITNAME = 42x0.380 (low resolution)
                slitlen, slitwidt = slitname.split('x')

                #SLITNAME = 0.144x12 (high resolution)
                if slitwidt > slitlen:
                    slitlen, slitwidt = slitwidt, slitlen

                dispers = self.get_keyword('DISPERS')
                if dispers == 'low':
                    specres = lowres[str(slitwidt.rstrip('0'))]
                elif dispers == 'high':
                    width = str(slitwidt)
                    if self.get_keyword('ISAO') == 'yes':
                        width = highres[width]
                    specres = round(10800/float(slitwidt))

                specres = int(specres)
                slitlen = float(slitlen)
                slitwidt = float(slitwidt)

        self.set_keyword('SLITLEN', slitlen, 'KOA: Slit length projected on sky (arcsec)')
        self.set_keyword('SLITWIDT', slitwidt, 'KOA: Slit width projected on sky (arcsec)')
        self.set_keyword('SPECRES', specres, 'KOA: Nominal spectral resolution')

        return True


    def set_gain_and_readnoise(self):
        '''
        Sets the measured values for gain and read noise

        Note from GregD (20190429) - still need to measure RN for SCAM,
        leave null for now
        '''

        gain = 2.85
        readnoise = 'null'

        if self.prefix == 'NS':
            readnoise = 10.8

        self.set_keyword('DETGAIN', gain, 'KOA: Detector gain')
        self.set_keyword('DETRN', readnoise, 'KOA: Detector read noise')

        return True

