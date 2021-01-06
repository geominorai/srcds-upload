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

def addmap(mapname):
	map_edits = [
		Insert(
			file		= '/tf/cfg/mapcycle.txt',
			text		= mapname+'\n'
		),

		FindDuplicates(
			file		= '/tf/cfg/mapcycle.txt',
			search		= '[\\w_]+',
			remove		= True,
			failover	= None
		),

		Sort(
			file		= '/tf/cfg/mapcycle.txt',
		)
	]

	edit_run(servers, map_edits, backup, max_backups, read_only, rcon)

def replacemap(oldmap, newmap):
	map_edits = [
		Replace(
			file		= '/tf/cfg/mapcycle.txt',
			search		= oldmap,
			replace		= newmap
		)
	]

	edit_run(servers, map_edits, backup, max_backups, read_only, rcon)

def removemap(mapname):
	map_edits = [
		Delete(
			file		= '/tf/cfg/mapcycle.txt',
			search		= mapname,
			failover	= None
		)
	]

	edit_run(servers, map_edits, backup, max_backups, read_only, rcon)

backup = True
max_backups = 10

read_only = False
rcon = ""

if __name__ == '__main__':
	edit_run(servers, edits, backup, max_backups, read_only, rcon)

	# addmap('plr_example_v1')
	# replacemap('plr_example_v1', 'plr_example_v2')
	# removemap('plr_example_v1')

	print('Done')
