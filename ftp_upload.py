import os, sys, stat
import logging

from paramiko import Transport, SFTPClient, RSAKey, AuthenticationException
from ftplib import FTP, error_perm
import valve.rcon

def upload_ftp(server_info, upload_files, delete_files, force_reupload=False):
	server, info = server_info

	try:
		ftp = FTP(info['host'])
	except RuntimeError:
		print("\t\tUnexpected error:", sys.exc_info()[0])
		return False, None, None
	
	ftp.login(info['username'], info['password'])
	ftp.set_pasv(True)
	
	if delete_files:
		print('\t\tProcessing %d deletions...' % (len(delete_files)))
		for i, d in enumerate(delete_files):
			print('\t\t\t%d.  %s' % (i+1, d))
			try:
				ftp.delete(d)
			except error_perm:
				continue
				try:
					ftp.rmd(d)
				except error_perm:
					continue
	
	plugins_load = []
	plugins_reload = []
	
	nlst_cache = {};

	lastpath = None
	for (path, file) in upload_files:
		relative_filepath = path + '/' + file
		print('\t\tProcessing %s' % file)
		
		if lastpath != path:
			try:
				ftp.cwd(path)
			except error_perm:
				print('\t\t\t%s does not exist, creating...' % path)
				i=1
				while i != -1:
					i = path.find('/', i)
					if i != -1:
						try:
							ftp.cwd(path[0:i])
							i += 1
						except error_perm:
							ftp.mkd(path[0:i])
							
				ftp.mkd(path)
				ftp.cwd(path)
				
			lastpath = path
		
		if relative_filepath in nlst_cache:
			files_online = nlst_cache[relative_filepath]
		else:
			files_online =  ftp.nlst()
			nlst_cache[relative_filepath] = files_online
		
		local_filepath = 'upload' + relative_filepath

		if file in files_online:
			print('\t\t\tRemote file found')

			upload = False
			if (force_reupload):
				print('\t\t\tForcing reupload')
				upload = True
			else:
				lsize = os.path.getsize(local_filepath)
				rsize = ftp.size(relative_filepath)

				if lsize != rsize:
					print('\t\t\tSize mismatch -- Reuploading')
					upload = True

			if upload:
				local_file = open(local_filepath, 'rb')
				ftp.storbinary('STOR ' + file, local_file)
				local_file.close()

				if (file[-4:] == '.smx'):
					plugins_reload.append(file[:-4])
		else:
			print('\t\t\tUploading')
			
			local_file = open(local_filepath, 'rb')
			ftp.storbinary('STOR ' + file, local_file)
			local_file.close()

			if (file[-4:] == '.smx'):
				plugins_load.append(file[:-4])
				
		
	
	ftp.close()
	print('\t\tLogout')
	
	return True, plugins_load, plugins_reload

def upload_sftp(server_info, upload_files, delete_files, force_reupload=False):
	server, info = server_info
	t = Transport((info['host'], info['port']))
	try:
		t.connect(username=info['username'], password=info['password'])
	except AuthenticationException as e:
		print('\t\t%s' % e)
		return False, [], []


	plugins_load = []
	plugins_reload = []

	sftp = SFTPClient.from_transport(t)
	try:
		sftp.chdir(info['path'])
	except FileNotFoundError as e:
		print('\t\tCannot chdir to remote path %s: %s' % (info['path'], e))
		return False, [], []

	if delete_files:
		print('\t\tProcessing %d deletions...' % (len(delete_files)))
		for i, d in enumerate(delete_files):
			print('\t\t\t%d. %s' % (i+1, d))
			try:
				file_info = sftp.stat(info['path'] + '/' + d)
				if stat.S_ISDIR(file_info.st_mode):
					sftp.rmdir(info['path'] + '/' + d)
				else:
					sftp.remove(info['path'] + '/' + d)
			except FileNotFoundError:
				pass
			except Exception as e:
				print('\t\t\t\tFailed: %s' % e)

	for (path, file) in upload_files:
		abs_path = info['path'] + '/' + path
		relative_filepath = path + '/' + file
		print('\t\tProcessing %s' % file)

		try:
			sftp.stat(abs_path)
		except FileNotFoundError:
			print('\t\t\t%s does not exist, creating...' % path)
			
			i=1
			while i != -1:
				i = path.find('/', i)
				abs_path = info['path'] + path[0:i]
				if i != -1:
					try:
						sftp.stat(abs_path)
						i += 1
					except FileNotFoundError:	
						sftp.mkdir(abs_path)
					
			sftp.mkdir(info['path'] + path)

		local_filepath = 'upload' + relative_filepath

		try:
			fileinfo = sftp.stat(info['path'] + relative_filepath)
			print('\t\t\tRemote file found')

			upload = False
			if (force_reupload):
				print('\t\t\tForcing reupload')
				upload = True
			else:
				lsize = os.path.getsize(local_filepath)
				rsize = fileinfo.st_size

				if lsize != rsize:
					print('\t\t\tSize mismatch -- Reuploading')
					upload = True

			if upload:
				sftp.put(local_filepath, info['path'] + relative_filepath)
				
				if (file[-4:] == '.smx'):
					plugins_reload.append(file[:-4])

		except FileNotFoundError:
			print('\t\t\tUploading')

			sftp.put(local_filepath, info['path'] + relative_filepath)

			if (file[-4:] == '.smx'):
				plugins_load.append(file[:-4])
	
	t.close()
	print('\t\tLogout')

	return True, plugins_load, plugins_reload
	
def run(servers, force_reupload=False, rcon_cmds='', delete_files=None):
	logger = logging.getLogger(valve.rcon.__name__)
	logger.setLevel(logging.ERROR)

	if (not os.path.isdir('upload')):
		os.mkdir('upload')
	
	upload_files = []
	for i, (path, dirs, files) in enumerate(os.walk('upload')):
		for f in files:
			upload_files.append(('/' + path[7:].replace('\\', '/'), f))

	print('Discovered %d files in uploads folder' % len(upload_files))
	for i, file in enumerate(upload_files):
		print('\t%d: %s' % (i+1, file))
	
	print('Logging into %d servers...' % len(servers))

	for i, (server, info) in enumerate(servers.items()):
		host = info['host']
		port = info['ext_port'] if 'ext_port' in info else 27015

		print('\t%d. %-20s [%s:%d]' % (i+1, server, host, port))
		
		success = False

		if upload_files or delete_files:
			try:
				if 'protocol' in info:
					protocol = info['protocol'].lower()
				else:
					protocol = 'ftp'

				if protocol == 'ftp':
					success, plugins_load, plugins_reload = upload_ftp((server, info), upload_files, delete_files, force_reupload)
				elif protocol == 'sftp':
					success, plugins_load, plugins_reload = upload_sftp((server, info), upload_files, delete_files, force_reupload)
				else:
					raise ValueError('Protocol must be ftp or sftp')

			except Exception as e:
				print('\t\tError while uploading: %s' % e)
		else:
			success, plugins_load, plugins_reload = True, [], []
			
		if success and 'rcon' in info and (rcon_cmds or plugins_load or plugins_reload):
			address = info['ext_ip'] if 'ext_ip' in info else host

			retry = 3
			while retry > 0:
				try:
					with valve.rcon.RCON((address, port), info['rcon']) as rcon:
						for plugin in [p for p in plugins_load if p not in plugins_reload]:
							print('\t\tRCON: %s' % rcon('sm plugins load "%s"' % plugin))
						for plugin in plugins_reload:
							print('\t\tRCON: %s' % rcon('sm plugins reload "%s"' % plugin))

						if rcon_cmds:
							print('\t\tRCON:\t%s' % rcon(rcon_cmds).replace('\n','\n\t\t\t'))
						
						retry = 0
				except valve.rcon.RCONAuthenticationError as e:
					print('\t\tRcon failed: %s'% e)
					retry = 0
				except valve.rcon.RCONError as e:
					print('\t\tRcon failed: %s'% e)
					print('\t\tRetrying rcon')
					retry = retry -1
				except TimeoutError as e:
					print('\t\tRcon timeout: %s'% e)
					retry = 0
				except ConnectionError as e:
					print('\t\tConnection failed: %s'% e)
					retry = 0
