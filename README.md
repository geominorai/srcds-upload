# srcds-upload
Automate multi-server FTP/SFTP file uploads and text file editing for Source dedicated servers

### ftp_upload
#### Usage
* Add files to upload folder according to folder structure seen after login, e.g. `/tf`.  New folders will automatically be created.
* Fill `ftp_logins` with ftp/sftp login and rcon information for the servers.  See the file for examples of the required fields.
* Edit `ftp_upload_run` to define list of servers to upload to, along with optional rcon commands (Sourcemod plugins will automatically be loaded/reloaded)
* Set `force_reupload` to `True` to ignore file size check and upload anyway.  (Useful when the file size has not changed since we can only compare files by size in FTP)
* Include the full path to the file for `delete` list of file deletions, e.g. `/tf/addons/sourcemod/plugins/myplugin.smx`
* Plugin deletions are not automatically unloaded.  You will have to set `rcon` with a command like `sm plugins unload myplugin`.
* Execute `python ftp_upload_run`

### ftp_edit
#### Usage
* Fill `ftp_logins` with ftp/sftp login and rcon information for the servers.  See the file for examples of the required fields.
* Edit `ftp_edit_run` to define list of servers to connect to, along with optional rcon commands
* Add to `edits` the list of sequential operations to run on each server.
* Operations can be chained in the event of failure.  (See the Replace with Insert failover example.)
* Set `read_only` to `True` for a dry run without uploading changes.
* Set `backup` to `True` to enable backup of files prior to uploading changes (or a Backup operation).  These are sorted per server folder in `backups/<date>-<time>/<server>`.
* Set `max_backups` to the number of backups to keep.  Each run that writes at least one backup file counts as one backup.

#### Edit Operations
* `Command` - Send one or more rcon commands to the server
* `Backup` - Create a backup of the specified `file`.  `backup` variable at the bottom must be set to `True`
* `Print` - Dump the contents of the text file to console.
* `Sort` - Sorts the lines in the text file alphabetically (without blank lines).
* `Find` - Search the text file with regex `search`
* `FindDuplicates` - Search the text file with regex `search` and remove subsequent lines with duplicate matches.
* `Insert` - Insert a line into the text file relative to regex `after`, `before`, or at the end of the file if neither are specified.
* `Replace` - Replace a line in the text file matching regex `search` with `replace` (regex capture groups permitted)
* `Delete` - Delete a line in the text file matching regex `search`
* All edit operations support `failover` of another Edit Operation and `rcon` for rcon commands (string or list of strings)

### Extra
* Run `clear_uploads.sh` to clear the files in the upload folder while preserving the empty folders for future use.

### Dependencies
* [ftplib](https://docs.python.org/3/library/ftplib.html)
* [python-valve](https://github.com/serverstf/python-valve)
* [paramiko](https://github.com/paramiko/paramiko)
