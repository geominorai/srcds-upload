import ftp_upload
from ftp_logins import logins_ftp

# Filter servers by group
servers = {  
	     **logins_ftp['koth'], \
	     # **logins_ftp['ht']
	    }

# Filter servers by name
# servers = {k:v for k,v in servers.items() if 'EU' in k}

force_reupload = False
rcon_cmds = ""
delete = []

if __name__ == '__main__':
	ftp_upload.run(servers, force_reupload, rcon_cmds, delete)
	print('Done')
