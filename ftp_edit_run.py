from ftp_edit import *
from ftp_logins import logins_ftp

# Filter servers by group
servers = {
	     **logins_ftp['koth'], \
	     # **logins_ftp['ht']
	    }

# Filter servers by name
# servers = {k:v for k,v in servers.items() if 'EU' in k}

edits = [
			# Command(
			# 	rcon		= ['status', 'version']
			# ),

			# Backup(
			# 	file		= '/tf/cfg/server.cfg',
			# ),

			# Print(
			# 	file		= '/tf/cfg/server.cfg',
			# ),

			# Sort(
			# 	file		= '/tf/cfg/mapcycle.txt',
			# )

			# Find(
			# 	file		= '/tf/cfg/server.cfg',
			# 	search		= 'sv_noclipspeed',
			# 	failover	= None
			# ),

			# FindDuplicates(
			# 	file		= '/tf/cfg/mapcycle.txt',
			# 	search		= '[\\w_]+',
			# 	# remove	= True,
			# 	failover	= None
			# ),

			# Insert(
			# 	file		= '/tf/cfg/server.cfg',
			# 	text		= 'sv_noclipspeed 10',
			# 	# before	= 'sv_maxrate',
			# 	after		= 'sv_cheats',
			# 	failover	= Print()
			# ),

			Replace(
				file		= '/tf/cfg/server.cfg',
				search		= '(sv_noclipspeed) \\d+',
				replace		= '\\1 10',
				rcon		= 'exec server',
				failover	= Insert(
									text='sv_noclipspeed 10',
									after='sv_cheats',
									rcon='exec server'
							  )
			),

			# Delete(
			# 	file		= '/tf/cfg/server.cfg',
			# 	search		= '(sv_noclipspeed) \\d+',
			# 	failover	= None
			# ),
		]

backup = True
max_backups = 10

read_only = False
rcon = ""

if __name__ == '__main__':
	edit_run(servers, edits, backup, max_backups, read_only, rcon)
	print('Done')
