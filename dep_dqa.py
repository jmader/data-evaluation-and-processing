"""
  This script consolidates all the pieces of the KOA data quality
  assessment into one place. Upon completion, it should populate the
  process directory with the final FITS files, in some cases adding 
  header keywords where necessary.

  Usage: dep_dqa(instrObj, tpx)

  Original scripts written by Jeff Mader and Jennifer Holt
  Ported to Python3 by Matthew Brown and Josh Riley
"""
import os
import sys
import getProgInfo as gpi
from create_prog import *
import shutil
from common import *
from datetime import datetime as dt
import metadata
import re
import hashlib
import configparser
from astropy.io import fits


def dep_dqa(instrObj, tpx=0):
    """
    This function will analyze the FITS file to determine if they will be
    archived and if they need modifications or additions to their headers.

    @type instrObj: instrument
    @param instr: The instrument object
    """

    #define vars to use throughout
    instr  = instrObj.instr
    utDate = instrObj.utDate
    log    = instrObj.log
    dirs   = instrObj.dirs
    utDateDir = instrObj.utDateDir
    isDev = int(instrObj.config['RUNTIME']['DEV'])
    sciFiles = 0
    inFiles = []
    outFiles = []
    procFiles = []
    semids = []
    extraMeta = {}
    dqaFile = dirs['stage'] +'/dep_dqa' + instr +'.txt'
    useHdrProg = instrObj.config['MISC']['USE_HDR_PROG'] if 'USE_HDR_PROG' in instrObj.config['MISC'] else None
    splitTime = instrObj.config['MISC']['SPLIT_TIME'] if 'SPLIT_TIME' in instrObj.config['MISC'] else None


    #Log start
    log.info('dep_dqa.py started for {} {}'.format(instr, utDate))


    #todo: check for existing output files and error out with warning?


    # Error if locate file does not exist (required input file)
    locateFile = dirs['stage'] + '/dep_locate' + instr + '.txt'
    if not os.path.exists(locateFile):
        raise Exception('dep_dqa.py: locate input file does not exist.  EXITING.')
        return
        

    # Read the list of FITS files
    files = []
    with open(locateFile, 'r') as locatelist:
        for line in locatelist:
            files.append(line.strip())


    #if no files, then exit out
    if len(files) == 0 :
        notify_zero_files(instrObj, dqaFile, tpx, log)
        return


    #determine program info
    create_prog(instrObj)
    progData = gpi.getProgInfo(utDate, instr, dirs['stage'], useHdrProg, splitTime, log)


    # Loop through each entry in input_list
    log.info('dep_dqa.py: Processing {} files'.format(len(files)))
    for filename in files:

        log.info('dep_dqa.py input file is {}'.format(filename))

        #Set current file to work on and run dqa checks, etc
        ok = True
        if ok: ok = instrObj.set_fits_file(filename)
        if ok: ok = instrObj.run_dqa_checks(progData)
        if ok: ok = check_koaid(instrObj, outFiles, log)
        if ok: ok = instrObj.write_lev0_fits_file()
        if ok: instrObj.make_jpg()

 
        #If any of these steps return false then copy to udf and skip
        if (not ok): 
            log.warning('FITS file failed DQA.  Copying {} to {}'.format(filename, dirs['udf']))
            shutil.copy2(filename, dirs['udf']);
            continue

        #keep list of good fits filenames
        procFiles.append(instrObj.fitsFilepath)
        inFiles.append(os.path.basename(instrObj.fitsFilepath))
        koaid = instrObj.fitsHeader.get('KOAID')
        if koaid.startswith('NC'): koaid = '/'.join(('scam', koaid))
        elif koaid.startswith('NS'): koaid = '/'.join(('spec', koaid))
        outFiles.append(koaid)
#        outFiles.append(instrObj.fitsHeader.get('KOAID'))
        semids.append(instrObj.get_semid())

        #stats
        if instrObj.is_science(): sciFiles += 1

        #deal with extra metadata
        koaid = instrObj.fitsHeader.get('KOAID')
        extraMeta[koaid] = instrObj.extraMeta


    #if no files passed DQA, then exit out
    if len(outFiles) == 0 :
        notify_zero_files(instrObj, dqaFile, tpx, log)
        return


    #log num files passed DQA and write out list to file
    log.info('dep_dqa.py: {} files passed DQA'.format(len(procFiles)))
    with open(dqaFile, 'w') as f:
        for path in procFiles:
            f.write(path + '\n')


    #Create yyyymmdd.filelist.table
    fltFile = dirs['lev0'] + '/' + utDateDir + '.filelist.table'
    with open(fltFile, 'w') as fp:
        for i in range(len(inFiles)):
            fp.write(inFiles[i] + ' ' + outFiles[i] + "\n")
        fp.write("    " + str(len(inFiles)) + ' Total FITS files\n')


    #create metadata file
    log.info('make_metadata.py started for {} {} UT'.format(instr.upper(), utDate))
    tablesDir = instrObj.metadataTablesDir
    ymd = utDate.replace('-', '')
    metaOutFile =  dirs['lev0'] + '/' + ymd + '.metadata.table'
    keywordsDefFile = tablesDir + '/keywords.format.' + instr
    metadata.make_metadata( keywordsDefFile, metaOutFile, dirs['lev0'], extraMeta, log, 
                            dev=isDev,
                            instrKeywordSkips=instrObj.keywordSkips)    


    #Create the extension files
    make_fits_extension_metadata_files(dirs['lev0']+ '/', md5Prepend=utDateDir+'.', log=log)


    #Create yyyymmdd.FITS.md5sum.table
    md5Outfile = dirs['lev0'] + '/' + utDateDir + '.FITS.md5sum.table'
    log.info('dep_dqa.py creating {}'.format(md5Outfile))
    make_dir_md5_table(dirs['lev0'], ".fits", md5Outfile)


    #Create yyyymmdd.JPEG.md5sum.table
    md5Outfile = dirs['lev0'] + '/' + utDateDir + '.JPEG.md5sum.table'
    log.info('dep_dqa.py creating {}'.format(md5Outfile))
    make_dir_md5_table(dirs['lev0'], ".jpg", md5Outfile)


    #get sdata number lists and PI list strings
    piList = get_tpx_pi_str(progData)
    sdataList = get_tpx_sdata_str(progData)


    #update TPX
    #NOTE: dep_tar will mark as archive ready once all is zipped, etc
    if tpx:
        log.info('dep_dqa.py: updating tpx DB records')
        utcTimestamp = dt.utcnow().strftime("%Y%m%d %H:%M")
        update_koatpx(instr, utDate, 'files_arch', str(len(procFiles)), log)
        update_koatpx(instr, utDate, 'pi', piList, log)
        update_koatpx(instr, utDate, 'sdata', sdataList, log)
        update_koatpx(instr, utDate, 'sci_files', str(sciFiles), log)


    #update koapi_send for all unique semids
    #NOTE: ensure this doesn't trigger during testing
    #TODO: Should this go in koaxfr?
    if tpx and not isDev:
        check_koapi_send(semids, instrObj.utDate, instrObj.config['API']['koaapi'], log)


    #log success
    log.info('dep_dqa.py DQA Successful for {}'.format(instr))


def make_fits_extension_metadata_files(inDir='./', outDir=None, endsWith='.fits', log=None, md5Prepend=''):
    '''
    Creates IPAC ASCII formatted data files for any extended header data found.
    '''
    #todo: put in warnings for empty ext headers


    if log: log.info('dep_dqa.py: making FITS extension metadata files from dir: ' + inDir)

    #outdir is indir?
    if outDir == None: outDir = inDir

    #remove existing *.ext*.table files and md5sum file
    removeFilesByWildcard(outDir +'*.ext*.table')

    #find all FITS files in inDir
    filepaths = []
    for file in sorted(os.listdir(inDir)):
        if (file.endswith(endsWith)): 
            filepaths.append(inDir + '/' + file)

    #for each file, read extensions and write to file
    hduNames = []
    extFullList = []
    for filepath in filepaths:
            file = os.path.basename(filepath)
            hdus = fits.open(filepath)
            for i in range(0, len(hdus)):
                #wrap in try since some ext headers have been found to be corrupted
                try:
                    hdu = hdus[i]
                    if 'TableHDU' not in str(type(hdu)): continue

                    #keep track of hdu names processed
                    if hdu.name not in hduNames: hduNames.append(hdu.name)

                    #calc col widths
                    dataStr = ''
                    colWidths = []
                    for idx, colName in enumerate(hdu.data.columns.names):
                        fmtWidth = int(hdu.data.formats[idx][1:])
                        colWidth = max(fmtWidth, len(colName))
                        colWidths.append(colWidth)

                    #add hdu name as comment
                    dataStr += '\ Extended Header Name: ' + hdu.name + "\n"

                    #add header
                    #TODO: NOTE: Found that all ext data is stored as strings regardless of type it seems to hardcoding to 'char' for now.
                    for idx, cw in enumerate(colWidths):
                        dataStr += '|' + hdu.data.columns.names[idx].ljust(cw)
                    dataStr += "|\n"
                    for idx, cw in enumerate(colWidths):
                        dataStr += '|' + 'char'.ljust(cw)
                    dataStr += "|\n"
                    for idx, cw in enumerate(colWidths):
                        dataStr += '|' + ''.ljust(cw)
                    dataStr += "|\n"
                    for idx, cw in enumerate(colWidths):
                        dataStr += '|' + ''.ljust(cw)
                    dataStr += "|\n"

                    #add data rows
                    for j in range(0, len(hdu.data)):
                        row = hdu.data[j]
                        for idx, cw in enumerate(colWidths):
                            valStr = row[idx]
                            dataStr += ' ' + str(valStr).ljust(cw)
                        dataStr += "\n"

                    #write to outfile
                    outFile = file.replace(endsWith, '.ext' + str(i) + '.' + hdu.name + '.tbl')
                    outFilepath = outDir + outFile
                    extFullList.append(outFilepath)
                    with open(outFilepath, 'w') as f:
                        f.write(dataStr)
                except:
                    if log: log.error(f'Could not create extended header table for ext header index {i} for file {file}!')


    #Create ext.md5sum.table
    if len(extFullList) > 0:
        md5Outfile = outDir + md5Prepend + 'ext.md5sum.table'
        if log: log.info('dep_dqa.py creating {}'.format(md5Outfile))
        make_dir_md5_table(outDir, None, md5Outfile, regex='.ext\d')



def check_koapi_send(semids, utDate, apiUrl, log):
    '''
    Sends all unique semids processed in DQA to KOA api to flag semids
    for needing an email sent to PI that there data has been archived
    '''

    user = os.getlogin()
    myHash = hashlib.md5(user.encode('utf-8')).hexdigest()

    #loops thru semids, skipping duplicates
    processed = []
    for semid in semids:

        if semid in processed: continue

        #check if we should update koapi_send
        semester, progid = semid.upper().split('_')
        if progid == 'NONE' or progid == 'null' or progid == 'ENG' or progid == '':
            continue;
        if progid == None or semester == None:
            continue;

        #koa api url
        url = apiUrl
        url += 'cmd=updateKoapiSend'
        url += '&utdate=' + utDate
        url += '&semid='  + semid
        url += '&hash='   + myHash

        #call and check results
        log.info('check_koapi_send: calling koa api url: {}'.format(url))
        result = get_api_data(url)
        if result == None or result == 'false':
            log.error('check_koapi_send failed')

        processed.append(semid)



def check_koaid(instrObj, koaidList, log):

    #sanity check
    koaid = instrObj.fitsHeader.get('KOAID')
    if (koaid == False or koaid == None):
        log.error('dep_dqa.py: BAD KOAID "{}" found for {}'.format(koaid, instrObj.fitsFilepath))
        return False

    #check for duplicates
    if (koaid in koaidList):
        log.error('dep_dqa.py: DUPLICATE KOAID "{}" found for {}'.format(koaid, instrObj.fitsFilepath))
        return False

    #check that date and time extracted from generated KOAID falls within our 24-hour processing datetime range.
    #NOTE: Only checking outside of 1 day difference b/c file write time can cause this to trigger incorrectly
    prefix, kdate, ktime, postfix = koaid.split('.')
    hours, minutes, seconds = instrObj.endTime.split(":") 
    endTimeSec = float(hours) * 3600.0 + float(minutes)*60.0 + float(seconds)
    idate = instrObj.utDate.replace('/', '-').replace('-', '')

    a = dt.strptime(kdate[:4]+'-'+kdate[4:6]+'-'+kdate[6:8], "%Y-%m-%d")
    b = dt.strptime(idate[:4]+'-'+idate[4:6]+'-'+idate[6:8], "%Y-%m-%d")
    delta = b - a
    delta = abs(delta.days)

    if (kdate != idate and delta > 1 and float(ktime) < endTimeSec):
        log.error('dep_dqa.py: KOAID "{}" has bad Date "{}" for file {}'.format(koaid, kdate, instrObj.fitsFilepath))
        return False

    return True



def notify_zero_files(instrObj, dqaFile, tpx, log):

    #log
    log.info('dep_dqa.py: 0 files output from DQA process.')

    #touch empty output file
    open(dqaFile, 'a').close()

    #tpx update
    if tpx:
        log.info('dep_dqa.py: updating tpx DB records')
        utcTimestamp = dt.utcnow().strftime("%Y%m%d %H:%M")
        update_koatpx(instrObj.instr, instrObj.utDate, 'arch_stat', 'DONE', log)
        update_koatpx(instrObj.instr, instrObj.utDate, 'arch_time', utcTimestamp, log)



def get_tpx_sdata_str(progData):
    '''
    Finds unique sdata directory numbers and creates string for DB
    ex: "123/456"
    '''
    items = []
    for row in progData:
        filepath = row['file']
        match = re.search( r'/sdata(.*?)/', filepath, re.I)
        if match:
            item = match.groups(1)[0]
            if item not in items:
                items.append(item)

    text = '/'.join(items)
    if text == '': text = 'NONE'
    return text


def get_tpx_pi_str(progData):
    '''
    Finds unique PIs and creates string for DB
    ex: "Smith/Jones"
    '''
    items = []
    for row in progData:
        pi = row['progpi']
        if pi not in items:
            items.append(pi)

    text = '/'.join(items)
    if text == '': text = 'NONE'
    return text


