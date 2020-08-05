#!/usr/bin/env python3

""" iCloud Drive ftp client

A command line ftp-styled client for iCloud Drive.
Needs latest pyicloud from https://github.com/ixs/pyicloud until PR is merged.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""

import cmd
import click
import datetime
import logging
import netrc
import os
import os.path
import time
import shlex
from pprint import pprint
from pyicloud import PyiCloudService
from shutil import copyfileobj


class Iftp(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        self._sort = True
        self.prompt = "iftp> "
        self._api = None
        self._netrc = netrc.netrc()
        self.path = []
        self.user_path = "/"

    def do_login(self, args):
        """Login into iCloud"""
        try:
            self.username, _, self.password = self._netrc.authenticators("icloud")
        except TypeError:
            self.username = click.prompt("iCloud Username")
            self.password = click.prompt("iCloud Password")
        self._login()

    def do_ls(self, args):
        """List files"""
        if not self.check_login():
            print("Not logged in, login first")
            return

        if args == '':
            args = self.user_path
        else:
            args = os.path.normpath(os.path.join(self.user_path, args))
        path = self._get_handle_for_path(args)
        if path:
            for item in path.dir():
                drive_file = path[item]
                if drive_file.type == "file":
                    perms = "-rw-rw-rw-"
                    size = drive_file.size
                    date = drive_file.date_modified
                    if date.year == datetime.datetime.now().year:
                        filedate = date.strftime("%b %d %H:%S")
                    else:
                        filedate = date.strftime("%b %d  %Y")
                elif drive_file.type == "folder":
                    perms = "drwxrwxrwx"
                    size = 0
                    filedate = "Jan 01  1970"
                print(
                    "%s %-4s %5s %-5s %13s %s %s"
                    % (perms, 0, os.getuid(), os.getgid(), size, filedate, drive_file.name)
                )
        return

    def do_get(self, args):
        """Download file"""
        if not self.check_login():
            print("Not logged in, login first")
            return

        args = os.path.normpath(os.path.join(self.user_path, args))
        drive_handle = self._get_handle_for_path(args)
        if drive_handle and drive_handle.type == 'file':
            starttime = time.time()
            with drive_handle.open(stream=True) as response:
                with open(drive_handle.name, "wb") as file_out:
                    copyfileobj(response.raw, file_out)
            stoptime = time.time()
            duration = stoptime - starttime
            print("%s bytes received in %f secs (%f Kbytes/sec)" % (drive_handle.size, duration, drive_handle.size / duration / 1024))
        else:
            print("550 Failed to open file.")
        return

    def do_mkdir(self, args):
        """Create new directory"""
        if not self.check_login():
            print("Not logged in, login first")
            return

        head, tail = os.path.split(args)
        if head:
             drive_handle = self._get_handle_for_path(os.path.normpath(os.path.join(self.user_path, head)))
        else:
             drive_handle = self._get_handle_for_path(self.user_path)
        if drive_handle and drive_handle.type == 'folder':
            drive_handle.mkdir(tail)
        print('257 "%s" created' % os.path.normpath(os.path.join(self.user_path, head, tail)))

    def do_rmdir(self, args):
        """Delete a directory"""
        if not self.check_login():
            print("Not logged in, login first")
            return

        args = os.path.normpath(os.path.join(self.user_path, args))
        drive_handle = self._get_handle_for_path(args)
        if drive_handle and drive_handle.type == 'folder':
            drive_handle.delete()
            print("250 Remove directory operation successful.")
        else:
            print("550 Remove directory operation failed.")

    def do_delete(self, args):
        """Delete a file"""
        if not self.check_login():
            print("Not logged in, login first")
            return

        args = os.path.normpath(os.path.join(self.user_path, args))
        drive_handle = self._get_handle_for_path(args)
        if drive_handle and drive_handle.type == 'file':
            drive_handle.delete()
            print("250 Delete operation successful.")
        else:
            print("550 Delete operation failed.")

    def do_rename(self, args):
        """Rename a file or folder"""
        if not self.check_login():
            print("Not logged in, login first")
            return

        sfile, dfile = shlex.split(args)
        args = os.path.normpath(os.path.join(self.user_path, sfile))
        drive_handle = self._get_handle_for_path(args)
        drive_handle.rename(os.path.basename(dfile))
        print("250 Rename successful.")

    def do_pwd(self, args):
        """Show current directory"""
        if not self.check_login():
            print("Not logged in, login first")
            return

        print('%s "%s"' % (257, self.user_path))

    def do_cd(self, args):
        """Change directory"""
        if not self.check_login():
            print("Not logged in, login first")
            return

        path = os.path.normpath(os.path.join(self.user_path, args))
        drive_handle = self._get_handle_for_path(path)
        if drive_handle and drive_handle.type == "folder":
            print('%s "%s"' % (250, "Directory successfully changed."))
            self.user_path = path
        else:
            print("%s %s" % (550, "Failed to change directory."))
        return

    def do_quit(self, args):
        return -1

    def do_EOF(self, args):
        return -1

    def check_login(self):
        if self._api is None:
            return False
        return True

    def _login(self):
        self._api = PyiCloudService(self.username, self.password)

        if self._api.requires_2sa:
            print("Two-factor authentication required. Your trusted devices are:")
            devices = self._api.trusted_devices
            for i, device in enumerate(devices):
                print(
                    "  %s: %s"
                    % (
                        i,
                        device.get("deviceName", "SMS to %s")
                        % device.get("phoneNumber"),
                    )
                )

            device = click.prompt("Which device would you like to use?", default=0)
            device = devices[device]
            if not self._api.send_verification_code(device):
                print("Failed to send verification code")
                sys.exit(1)

            code = click.prompt("Please enter validation code")
            if not self._api.validate_verification_code(device, code):
                print("Failed to verify verification code")
                sys.exit(1)
        print("Logged into iCloud Drive as %s" % self.username)

    def _verify_path(self, path):
        pass

    def _get_handle_for_path(self, args):
        """Get a drive API handle for a path"""
        drive_handle = self._api.drive

        # Handle '/' and just return the base drive_handle
        if args.strip() == '/':
            return drive_handle

        tmppath = args.split("/")
        # Cut leading /
        if tmppath[0] == "" and len(tmppath) > 1:
            tmppath.pop(0)

        try:
            for element in tmppath:
                drive_handle = drive_handle[element]
            return drive_handle
        except KeyError:
            return False

if __name__ == "__main__":
    Iftp().cmdloop()
