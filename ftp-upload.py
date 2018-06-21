import os, sys
from ftplib import FTP, error_perm
from ftp_logins import logins_ftp
from srcds.rcon import RconConnection

servers0 = logins_ftp['koth'].items()\
				+  logins_ftp['ht'].items()

# servers = [(k,v) for k,v in servers if 'NA' in v['name']] 
servers = servers0

force_reupload = False
rcon = ""
rcon_password = ''
delete = []

if __name__ == '__main__':
	if (not os.path.isdir('upload')):
		os.mkdir('upload')
	
	upload_files = []
	for i, (path, dirs, files) in enumerate(os.walk('upload')):
		for f in files:
			upload_files.append(('/' + path[7:].replace('\\', '/'), f))

	print 'Discovered %d files in uploads folder' % len(upload_files)
	for i, file in enumerate(upload_files):
		print '\t%d: %s' % (i+1, file)
	
	print 'Logging into FTP servers'
	for server, info in servers:
		print '\t', server
		
		try:
			ftp = FTP(server)
		except RuntimeError:
			print("Unexpected error:", sys.exc_info()[0])
			continue
		
		ftp.login(info['username'], info['password'])
		ftp.set_pasv(True)
		
		for d in delete:
			try:
				ftp.delete(d)
				print 'Deleted %s from %s' % (d, server)
			except error_perm:
				continue
				try:
					ftp.rmd(d)
					print 'Deleted %s from %s' % (d, server)
				except error_perm:
					continue
		
		plugins_load = []
		plugins_reload = []
		
		lastpath = None
		for (path, file) in upload_files:
			relative_filepath = path + '/' + file
			print '\t\tProcessing ', file
			
			if lastpath != path:
				try:
					ftp.cwd(path)
				except error_perm:
					print '\t\t\t%s does not exist, creating...' % (path)
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
			
			if force_reupload:
				files_online = None
			else:
				files_online =  ftp.nlst()
			
			local_filepath = 'upload' + relative_filepath
			local_file = open(local_filepath, 'rb')
			
			if (not force_reupload and file in files_online):
				print '\t\t\tRemote file found'
				lsize = os.path.getsize(local_filepath)
				rsize = ftp.size(relative_filepath)
				
				if force_reupload or (lsize != rsize):
					if force_reupload:
						print '\t\t\tForcing reupload'
					else:
						print '\t\t\tSize mismatch -- Reuploading'
					ftp.storbinary('STOR ' + file, local_file)
					if (file[-4:] == '.smx'):
						plugins_reload.append(file[:-4])
			else:
				if force_reupload:
					print '\t\t\tForcing reupload'
				else:
					print '\t\t\tUploading'
				ftp.storbinary('STOR ' + file, local_file)
				if (file[-4:] == '.smx'):
					plugins_load.append(file[:-4])
					if force_reupload:
						plugins_reload.append(file[:-4])
					
			local_file.close()
		
		ftp.close()
		print '\t\tLogout'
		
		if rcon_password and (rcon or plugins_load or plugins_reload):
			retry = 3
			while retry > 0:
				try:
					srv = RconConnection(server, password=rcon_password)

					for p in plugins_load:
						print('\t\tRCON: %s' % srv.exec_command('sm plugins load ' + p))
					for p in plugins_reload:
						print('\t\tRCON: %s' % srv.exec_command('sm plugins reload ' + p))

					if rcon:
						print('\t\tRCON: %s' % srv.exec_command(rcon))
					srv.disconnect()
					retry = 0
				except:
					retry = retry -1
					print '\t\tRetrying rcon'
				
	print 'Done'
