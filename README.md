# srcds-upload
Automate multi-server file uploads for Source dedicated servers

### Usage
* Add files to upload folder according to folder structure seen after login, e.g. `/tf`.  New folders will automatically be created.
* Fill `ftp_logins` with ftp/sftp login and rcon information for the servers.  See the file for examples of the required fields.
* Edit `ftp_upload_run` to define list of servers to upload to, along with rcon password and optional rcon commands (Sourcemod plugins will automatically be loaded/reloaded)
* Set `force_reupload` to `True` to ignore file size check and upload anyway.  (Useful when the file size has not changed since we can only compare files by size in FTP)
* Include the full path to the file for `delete` list of file deletions, e.g. `/tf/addons/sourcemod/plugins/myplugin.smx`
* Plugin deletions are not automatically unloaded.  You will have to set `rcon` with a command like `sm plugins unload myplugin`.
* Execute `python ftp_upload_run`

### Dependencies
* [ftplib](https://docs.python.org/3/library/ftplib.html)
* [python-valve](https://github.com/serverstf/python-valve)
* [paramiko](https://github.com/paramiko/paramiko)
