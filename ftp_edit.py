import os, sys, stat, shutil
import logging
import re
import tempfile
import time
import traceback

from paramiko import Transport, SFTPClient, RSAKey, AuthenticationException
from ftplib import FTP, error_perm
import valve.rcon

class Operation:
	def __init__(self, file=None, failover=None, rcon=None):
		self.file = file
		self.filename = os.path.basename(file) if file else None
		self.failover = failover
		self.rcon_cmd = rcon
		self.failed = False

	def run(self):
		self.failed = False

		if self.failover:
			self.failover.file = self.file
			self.failover.filename = self.filename

		return None

	def run_failover(self, fo):
		self.failed = True

		if self.failover:
			fo.seek(0)
			print('\t\tFailover: %s' % self.failover)

			return self.failover.run(fo)
		else:
			return None

	def rcon(self, info):
		if not self.failed:
			send_rcon(info, self.rcon_cmd, nest=2)
		elif self.failover:
			self.failover.rcon(info)


class Command(Operation):
	def __init__(self, rcon):
		super().__init__(None, None, rcon)

	def __str__(self):
		return "Send rcon command '%s'" % self.rcon_cmd


class Backup(Operation):
	def __init__(self, file):
		super().__init__(file, None, None)

	def __str__(self):
		return "Back up file: %s" % self.file


class Print(Operation):
	def __init__(self, file=None, search=None, failover=None, rcon=None):
		super().__init__(file, failover, rcon)

	def run(self, fo):
		super().run()

		for i, line in enumerate(fo):
			file_lineno = '%s:%d' % (self.filename, i+1)
			line = line.decode().rstrip()
			print('\t\t\t%-20s  %s' % (file_lineno, line))

		return None

	def __str__(self):
		return "Print contents of '%s'" % self.file


class Sort(Operation):
	def __init__(self, file=None, failover=None, rcon=None):
		super().__init__(file, failover, rcon)

	def run(self, fo):
		super().run()

		lines = [line.decode() for line in fo if line.strip()]
		lines.sort()

		tmp = tempfile.TemporaryFile(delete=False)
		try:
			for i, line in enumerate(lines):
				file_lineno = '%s:%d' % (self.filename, i+1)
				print('\t\t\t%-20s  %s' % (file_lineno, line.rstrip()))
				tmp.write(line.encode('utf-8'))
		finally:
			tmp.close()

		return tmp

	def __str__(self):
		return "Sort contents of '%s'" % self.file


class Find(Operation):
	def __init__(self, file=None, search=None, failover=None, rcon=None):
		super().__init__(file, failover, rcon)
		self.search = search
		self.re = re.compile(search)

	def run(self, fo):
		super().run()

		match_count = 0
		for i, line in enumerate(fo):
			line = line.decode().rstrip()
			match = self.re.match(line)
			if match:
				file_lineno = '%s:%d' % (self.filename, i+1)
				print('\t\t\t%-20s  %s' % (file_lineno, line))

				match_count += 1

		if not match_count:
			print('\t\t\tNo matches found')

			return self.run_failover(fo)

		return None

	def __str__(self):
		return "Find '%s' in '%s'" % (self.search, self.file)


class FindDuplicates(Operation):
	def __init__(self, remove=False, file=None, search=None, failover=None, rcon=None):
		super().__init__(file, failover, rcon)
		self.search = search
		self.re = re.compile(search)
		self.remove = remove

	def run(self, fo):
		super().run()

		lines = []
		for i, line in enumerate(fo):
			line = line.decode().strip()

			if self.search:
				match = self.re.match(line)
				if match and match.group(0) != 'exec':
					lines.append((i+1, line, match.group(0)))
			else:
				lines.append(i+1, line, line)


		n_lines = len(lines)
		duplicates = set()

		for i, (line_no, line, matched) in enumerate(lines[:-1]):
			if line_no in duplicates:
				continue

			n_duplicates = 0
			for (line_no0, line0, matched0) in lines[i+1:]:
				if line_no0 in duplicates:
					continue

				if matched == matched0:
					n_duplicates += 1
					if n_duplicates == 1:
						file_lineno = '%s:%d' % (self.filename, line_no)
						print('\t\t\t%-20s  %-40s' % (file_lineno, line))

					file_lineno = '%s:%d' % (self.filename, line_no0)
					print('\t\t\t%-20s  %-40s\t\t(Duplicate)' % (file_lineno, line0))

					duplicates.add(line_no0)

		if not duplicates:
			print('\t\t\tNo duplicates found')

			return self.run_failover(fo)

		if self.remove:
			tmp = tempfile.TemporaryFile(delete=False)

			try:
				fo.seek(0)
				for i, line in enumerate(fo):
					if i+1 not in duplicates:
						tmp.write(line)
			finally:
				tmp.close()

			return tmp

		return None

	def __str__(self):
		if self.remove:
			return "Find and remove duplicates in '%s'" % self.file
		return "Find duplicates in '%s'" % self.file


class Insert(Operation):
	def __init__(self, text, before=None, after=None, file=None, failover=None, rcon=None):
		super().__init__(file, failover, rcon)
		self.text = text
		if before and after:
			raise ValueError('Cannot insert both before and after')
		self.before = before
		self.after = after

		self.before_re = re.compile(before) if before else None
		self.after_re = re.compile(after) if after else None


	def run(self, fo):
		super().run()

		tmp = tempfile.TemporaryFile(delete=False)
		found = False

		newline = self.text + '\n'

		try:
			if self.before:
				for i, line in enumerate(fo):
					line = line.decode()

					if not found:
						match = self.before_re.match(line)
						if match:
							found = True

							tmp.write(newline.encode('utf-8'))

							file_lineno = '%s:%d' % (self.filename, i+1)
							print('\t\t\t%-20s  %s\t\t(Inserted)' % (file_lineno, self.text))

							file_lineno = '%s:%d' % (self.filename, i+2)
							print('\t\t\t%-20s  %s' % (file_lineno, line.rstrip()))

					tmp.write(line.encode('utf-8'))

			elif self.after:
				for i, line in enumerate(fo):
					line = line.decode()
					tmp.write(line.encode('utf-8'))

					if not found:
						match = self.after_re.match(line)
						if match:
							found = True

							tmp.write(newline.encode('utf-8'))

							file_lineno = '%s:%d' % (self.filename, i+1)
							print('\t\t\t%-20s  %s' % (file_lineno, line.rstrip()))

							file_lineno = '%s:%d' % (self.filename, i+2)
							print('\t\t\t%-20s  %s\t\t(Inserted)' % (file_lineno, self.text))

			else:
				i = -1
				for i, line in enumerate(fo):
					tmp.write(line)

				found = True

				tmp.write(newline.encode('utf-8'))

				file_lineno = '%s:%d' % (self.filename, i+2)
				print('\t\t\t%-20s  %s  (Inserted)' % (file_lineno, self.text))

		finally:
			tmp.close()

		if not found:
			print('\t\t\tNo matches found')
			os.remove(tmp.name)
			del tmp

			return self.run_failover(fo)

		return tmp

	def __str__(self):
		if self.before:
			return "Insert '%s' before '%s' in '%s'" % (self.text, self.before, self.file)
		elif self.after:
			return "Insert '%s' after '%s' in '%s'" % (self.text, self.after, self.file)
		else:
			return "Insert '%s' at the end in '%s'" % (self.text, self.file)


class Replace(Operation):
	def __init__(self, search, replace, file=None, failover=None, rcon=None):
		super().__init__(file, failover, rcon)
		self.search = search
		self.replace = replace
		self.re = re.compile(search)

	def run(self, fo):
		super().run()

		tmp = tempfile.TemporaryFile(delete=False)

		n_repl_count = 0

		try:
			for i, line in enumerate(fo):
				line = line.decode()
				line, n_repl = self.re.subn(lambda match: self.repl(i+1, match), line, count=1)
				tmp.write(line.encode('utf-8'))

				n_repl_count += n_repl
		finally:
			tmp.close()

		if not n_repl_count:
			print('\t\t\tNo matches found')
			os.remove(tmp.name)
			del tmp

			return self.run_failover(fo)

		return tmp

	def repl(self, line_no, match):
		s = match.start(0)
		e = match.end(0)

		line = match.string.rstrip()
		replaced = match.expand(self.replace)

		file_lineno = '%s:%d' % (self.filename, line_no)

		if match.group(0) == replaced:
			print('\t\t\t%-20s  %-40s\t\t(Unchanged)' % (file_lineno, line))
		else:
			print('\t\t\t%-20s  %-40s\t->\t%s%s%s\t\t(Replaced)' % (file_lineno, line, line[:s], replaced, line[e:]))
		return replaced

	def __str__(self):
		return "Replace '%s' with '%s' in '%s'" % (self.search, self.replace, self.file)


class Delete(Operation):
	def __init__(self, file=None, search=None, failover=None, rcon=None):
		super().__init__(file, failover, rcon)
		self.search = search
		self.re = re.compile(search)

	def run(self, fo):
		super().run()

		tmp = tempfile.TemporaryFile(delete=False)

		n_skip_count = 0

		try:
			for i, line in enumerate(fo):
				line = line.decode()
				match = self.re.match(line)
				if match:
					file_lineno = '%s:%d' % (self.filename, i+1)
					print('\t\t\t%-20s  %s\t\t(Deleted)' % (file_lineno, line.rstrip()))

					n_skip_count += 1
				else:
					tmp.write(line.encode('utf-8'))
		finally:
			tmp.close()

		if not n_skip_count:
			print('\t\t\tNo matches found')
			os.remove(tmp.name)
			del tmp

			return self.run_failover(fo)

		return tmp

	def __str__(self):
		return "Delete '%s' in '%s'" % (self.search, self.file)


def edit_ftp(server, info, edits, backup_path, read_only):
	ftp = FTP(info['host'])
	try:
		ftp.login(info['username'], info['password'])
		ftp.set_pasv(True)

		for edit in edits:
			if edit.file:
				abs_path_dir = os.path.dirname(edit.file)
				filename = os.path.basename(edit.file)

				try:
					ftp.cwd(abs_path_dir)
				except error_perm:
					print('\t\t\tPath %s does not exist' % abs_path_dir)
					return False

				with tempfile.TemporaryFile('rb+') as tmp:
					try:
						ftp.retrbinary('RETR ' + filename, tmp.write, 262144)
					except error_perm:
						raise FileNotFoundError

					if backup_path and isinstance(edit, Backup):
						backup_file(backup_path, server, edit.file, tmp)
						continue

					tmp.seek(0)

					print('\t\t%s' % edit)
					editedfile = edit.run(tmp)

					if editedfile:
						try:
							if read_only:
								print('\t\tRead-only')
							else:
								if backup_path:
									backup_file(backup_path, server, edit.file, tmp)

								print('\t\tUploading')

								with open(editedfile.name, 'rb') as fo:
									ftp.storbinary('STOR ' + filename, fo)
						finally:
							os.remove(editedfile.name)

			edit.rcon(info)

	finally:
		ftp.close()

	print('\t\tLogout')

	return True


def edit_sftp(server, info, edits, backup_path, read_only):
	t = Transport((info['host'], info['port']))
	try:
		t.connect(username=info['username'], password=info['password'])

		sftp = SFTPClient.from_transport(t)
		try:
			sftp.chdir(info['path'])
		except FileNotFoundError as e:
			print('\t\tCannot chdir to remote path %s: %s' % (info['path'], e))
			return False

		for edit in edits:
			if edit.file:
				abs_path_dir = info['path'] + '/' + os.path.dirname(edit.file)

				try:
					sftp.stat(abs_path_dir)
				except FileNotFoundError:
					print('\t\t\tPath %s does not exist' % abs_path_dir)
					return False

				abs_path_file = info['path'] + '/' + edit.file

				with tempfile.TemporaryFile('rb+') as tmp:
					sftp.getfo(abs_path_file, tmp)

					if backup_path and isinstance(edit, Backup):
						backup_file(backup_path, server, edit.file, tmp)
						continue

					tmp.seek(0)

					print('\t\t%s' % edit)
					editedfile = edit.run(tmp)

					if editedfile:
						try:
							if read_only:
								print('\t\tRead-only')
							else:
								if backup_path:
									backup_file(backup_path, server, edit.file, tmp)

								print('\t\tUploading')

								sftp.put(editedfile.name, abs_path_file)
						finally:
							os.remove(editedfile.name)

			edit.rcon(info)

	except AuthenticationException as e:
		print('\t\t%s' % e)
		return False

	finally:
		t.close()

	print('\t\tLogout')

	return True


def backup_cleanup(max_backups):
	if not os.path.isdir('backups') or max_backups is None or max_backups < 0:
		return

	dirs = [d for d in os.listdir('backups') if os.path.isdir('backups/%s' % d)]

	if len(dirs) > max_backups:
		dirs.sort(reverse=True)

		for d in dirs[max_backups:]:
			shutil.rmtree('backups/%s' % d)


def backup_file(backup_path, server_name, path, fo):
	abs_backup_path = '%s/%s/%s' % (backup_path, server_name, path)
	os.makedirs(os.path.dirname(abs_backup_path), exist_ok=True)

	if os.path.isfile(abs_backup_path):
		return

	print('\t\tSaving backup: %s' % abs_backup_path)
	with open(abs_backup_path, 'wb+') as b:
		fo.seek(0)
		shutil.copyfileobj(fo, b)


def send_rcon(info, cmds, retry=3, nest=0):
	if 'rcon' not in info or not cmds:
		return

	if isinstance(cmds, list):
		for cmd in cmds:
			send_rcon(info, cmd, retry, nest)
		return

	address = info['ext_ip'] if 'ext_ip' in info else info['host']
	port = info['ext_port'] if 'ext_port' in info else 27015

	padding = '\t' * nest

	while retry > 0:
		try:
			with valve.rcon.RCON((address, port), info['rcon']) as rcon:
				print('%sRCON:\t%s' % (padding, cmds))
				print('%s\t%s' % (padding, rcon(cmds).replace('\n','\n' + '\t'*(nest+1))))
				retry = 0
		except valve.rcon.RCONAuthenticationError as e:
			print('%sRcon failed: %s'% (padding, e))
			retry = 0
		except valve.rcon.RCONError as e:
			print('%sRcon failed: %s'% (padding, e))
			print('%sRetrying rcon' % padding)
			retry = retry -1
		except TimeoutError as e:
			print('%sRcon timeout: %s'% (padding, e))
			retry = 0
		except ConnectionError as e:
			print('%sConnection failed: %s'% (padding, e))
			retry = 0


def edit_run(servers, edits, backup=False, max_backups=10, read_only=False, rcon_cmds=''):
	logger = logging.getLogger(valve.rcon.__name__)
	logger.setLevel(logging.ERROR)

	edits = [e for e in edits if e.file or isinstance(e, Command) or isinstance(e, Backup)]

	n_files = len(edits)

	print('Editing %d %s %s backup...' % (n_files, 'files' if n_files>1 or not n_files else 'file', 'with' if backup else 'without'))
	for i, edit in enumerate(edits):
		print('\t%d: %s' % (i+1, edit))

	backup_path = 'backups/%s' % (time.strftime('%Y-%m-%d-%H%M%S', time.localtime())) if backup else None

	n_servers = len(servers)
	print('Logging into %d %s...' % (n_servers, 'servers' if n_servers>1 or not n_servers else 'server'))

	for i, (server, info) in enumerate(servers.items()):
		host = info['host']
		port = info['ext_port'] if 'ext_port' in info else 27015

		print('\t%d. %-20s [%s:%d]' % (i+1, server, host, port))

		success = False

		if edits:
			try:
				if 'protocol' in info:
					success = edit_sftp(server, info, edits, backup_path, read_only)
					pass
				else:
					success = edit_ftp(server, info, edits, backup_path, read_only)
					pass
			except FileNotFoundError as e:
				print('\t\tFile not found')
			except Exception as e:
				print('\t\tError while editing: %s' % e)
				traceback.print_exc()
		else:
			success = True

		if success:
			send_rcon(info, rcon_cmds, nest=2)

	backup_cleanup(max_backups)
