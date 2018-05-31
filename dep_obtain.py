from datetime import datetime, timedelta
from verification import *
import os
import json
import urllib.request
from common import url_get

def dep_obtain(instrObj):
    """
    Queries the telescope schedule database and creates the following files in stageDir:

    dep_obtainINSTR.txt
    dep_notschedINSTR.txt (if no entries found in database)

    @param instrObj: the instrument object
    @type instrObj: instrument class
    """

    log = instrObj.log
    log.info('dep_obtain: started for {} {} UT'.format(instrObj.instr, instrObj.utDate))

    # Get HST from utDate
    
    utDateObj = datetime.strptime(instrObj.utDate, '%Y-%m-%d')
    hstDateObj = utDateObj - timedelta(days=1)
    hstDate = hstDateObj.strftime('%Y-%m-%d')

    # Output files

    notScheduledFile = ''.join((instrObj.dirs['stage'], '/dep_notsched', instrObj.instr, '.txt'))
    obtainFile       = ''.join((instrObj.dirs['stage'], '/dep_obtain', instrObj.instr, '.txt'))

    try:

        # Read the telescope schedul URL

        schedUrl = ''.join((instrObj.telUrl, 'cmd=getSchedule', '&date=', hstDate, '&instr=', instrObj.instr))
        log.info('dep_obtain: retrieving telescope schedule info: {}'.format(schedUrl))
        schedData = url_get(schedUrl)
        if isinstance(schedData, dict): schedData = [schedData]

        # Get OA

        telnr = instrObj.get_telnr()
        oaUrl = ''.join((instrObj.telUrl, 'cmd=getNightStaff', '&date=', hstDate, '&telnr=', str(telnr), '&type=oa'))
        log.info('dep_obtain: retrieving night staff info: {}'.format(oaUrl))
        oaData = url_get(oaUrl)
        oa = 'None'
        if oaData:
            if isinstance(oaData, dict):
                if ('Alias' in oaData):
                    oa = oaData['Alias']
            else:
                for entry in oaData:
                    if entry['Type'] == 'oa':
                        oa = entry['Alias']

        # No entries found: Create stageDir/dep_notschedINSTR.txt and dep_obtainINSTR.txt

        if (schedData == None):
            log.info('dep_obtain: no telescope schedule info found for {}'.format(instrObj.instr))

            with open(notScheduledFile, 'w') as fp:
                fp.write('{} not scheduled'.format(instrObj.instr))

            with open(obtainFile, 'w') as fp:
                fp.write('{} {} NONE NONE NONE NONE NONE'.format(hstDate, oa))

        # Entries found: Create stageDir/dep_obtainINSTR.txt

        else:
            with open(obtainFile, 'w') as fp:
                num = 0
                for entry in schedData:

                    obsUrl = ''.join((instrObj.telUrl, 'cmd=getObservers', '&schedid=', entry['SchedId']))
                    log.info('dep_obtain: retrieving observers info: {}'.format(obsUrl))
                    obsData = url_get(obsUrl)

                    if obsData and len(obsData) > 0: observers = obsData[0]['Observers']
                    else                           : observers = 'None'

                    if num > 0: fp.write('\n')
                    fp.write('{} {} {} {} {} {} {}'.format(hstDate, oa, entry['Account'], entry['Institution'], entry['Principal'], entry['ProjCode'], observers))

                    log.info('dep_obtain: {} {} {} {} {} {} {}'.format(hstDate, oa, entry['Account'], entry['Institution'], entry['Principal'], entry['ProjCode'], observers))

                    num += 1

    except:
        log.info('dep_obtain: {} error reading telescope schedule'.format(instrObj.instr))
        return False

    return True
