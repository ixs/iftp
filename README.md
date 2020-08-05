iCloud Drive FTP client
=======================

This is a simple shot at a iCloud Drive FTP Client.
It's probably brittle as it was only written in a semi-defensible
style assuming that the user would never try to intentionally break it.
If you do, you gotta keep the pieces.
This is more proof of concept to write a FUSE filesystem but it works in the
meantime.

It's using pyicloud from https://github.com/picklepete/pyicloud but until
https://github.com/picklepete/pyicloud/pull/291 is merged, it's better to
use https://github.com/ixs/pyicloud/tree/drive_ops as that actually contains
the parts to modify drive files.


Installation
============

Easiest is to clone a copy and run everything from a virtual environment and use
pip to install dependencies:

```
git clone https://github.com/ixs/iftp.git
cd iftp
python3 -mvenv venv
. venv/bin/activate
pip3 install -r requirements.txt
```


Running
=======

```
cd iftp
. venv/bin/activate
./iftp.py
```

Supported commands are `login` (needs to happen first), `pwd`, `ls`, `cd`, `get`,
`put`, `mkdir`, `rmdir`, `delete`, `rename`.


netrc support
=============

`~/.netrc` is being read in order to automate the login flow. That way
the plaintext stored passwords can be used rather than having to type
it in all the time. This is naturally insecure.

File format is as follows:
```
machine icloud
login <icloud account login>
password <icloud account password>
```
