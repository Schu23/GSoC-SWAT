Howto
-----
1. Get the GIT scripts in the Download area
link: http://cloud.github.com/downloads/rvelhote/GSoC-SWAT/swat-git-scripts.tar.gz

2. run ./install
This will download and install Pylons into a Python Virtual Environment; Clone the GIT repository; Install the necessary dependencies for SWAT

3. run ./run
This will initiate the Server at http://localhost:5000. You must authenticate with a valid Samba account. Authentication will be performed using RPC or SAMR. If for some reason you can't authenticate, just go to http://localhost:5000/share/index because the authentication check is, for now, only in the dashboard.

There are also two other scripts called "pull" and "pull-and-run". 'pull' will just do a "git pull"; 'pull-and-run' will call the pull and run scripts. This will make sure you are up-to-date before you run SWAT.

Notes:
- Don't forget to chmod +x the scripts
- If you have problems saving information using the Classic Backend check the permissions for your smb.conf and directory, add SWAT to the Samba group (if it has one) or start SWAT as root if you want to try it.