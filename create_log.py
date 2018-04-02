import logging as lg
import os

def create_log(rootDir, instr, utDate):
	"""
	Creates and returns a log file handler

	@param rootDir: top directory where processed data will be written
	@type rootDir: string
	@param instr: instrument name
	@type instr: string
	@param utDate: UT date of observation
	@type utDate: string (yyyy-mm-dd)
	"""

	utDate = utDate.replace('/', '-')
	utDateDir = utDate.replace('-', '')

	# Where to create the log (rootDir/instr)

	processDir = ''.join((rootDir, '/', instr.upper()))

	# Setup logging

	user = os.getlogin()
	writerName = ''.join(('dep <', user, '>'))
	log_writer = lg.getLogger(writerName)
	log_writer.setLevel(lg.INFO)

	# Create a file handler

	logFile = ''.join((processDir, '/dep_', instr.upper(), '_', utDateDir, '.log'))
	log_handler = lg.FileHandler(logFile)
	log_handler.setLevel(lg.INFO)

	# Create logging format

	formatter = lg.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
	log_handler.setFormatter(formatter)

	# Add handler to the logger

	log_writer.addHandler(log_handler)

	log_writer.info('create_log.py log_writer created')

	return log_writer
