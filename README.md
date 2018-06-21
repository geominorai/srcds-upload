# srcds-upload
Automate multi-server file uploads

### Usage
* Add files to upload folder according to folder structure seen after login, e.g. `/tf`.  New folders will automatically be created.
* Edit script to define list of servers to upload to, along with rcon password and optional rcon commands (Sourcemod plugins will automatically be loaded/reloaded)
* Set `force_reupload` to `True` to ignore file size check and upload anyway.  (Useful when the file size has not changed since we can only compare files by size in FTP)

### Dependencies
* [pysrcds](https://github.com/pmrowla/pysrcds)
* [ftplib](https://docs.python.org/3/library/ftplib.html)
