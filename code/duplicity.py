"""Duplicity healper"""

from dataclasses import dataclass, field
from enum import Enum

import os
import copy
import time
import subprocess

from datetime import datetime

metric_template = {
    "running":           False,
    "lastBackup":           0,
    "elapseTime":           0,
    "timeSinceBackup":      0,
    "errors":               0,
    "files": {
        "new":              0, #NewFiles
        "deleted":          0, #DeletedFiles
        "changed":          0, #ChangedFiles
        "delta":            0  #DeltaEntries
    },
    "size": {
        "rawDelta":         0, #RawDeltaSize
        "changedFiles":     0, #ChangedFileSize
        "sourceFile":       0, #SourceFileSize
        "totalDestChange":  0  #TotalDestinationSizeChange
    }
}

class DuplicityBackupMethod(Enum):
    """An enum to control backup storage location connection type."""
    UNKNOWN = 0
    SSH = 1


@dataclass
class SSHParams():
    """Setup params for ssh params."""
    port:int = 22
    key_file:str = "/home/duplicity/config//id_rsa"
    user:str = "duplicity"
    host:str = "192.168.1.1"
    strict_host_key_checking:bool = False


@dataclass
class DuplicityLocationParams():
    """Setup params for duplicity location."""
    local_backup_path:str = ""
    pre_backup_date_file:str = ""
    restored_date_file:str = ""
    remote_path:str = "/home/duplicity/backup"


@dataclass
class DuplicityParams:
    """Setup params for dupliciy class."""
    backup_name:str = "duplicity"
    location_params:DuplicityLocationParams = field(defailt_factory=DuplicityLocationParams())
    full_if_older_than:str = ""
    verbosity:str = ""
    allow_source_mismatch:bool = True
    backup_method:DuplicityBackupMethod = DuplicityBackupMethod.SSH
    ssh_params:SSHParams = None


class Duplicity:
    """ Class to handle Duplicity commands. """
    def __init__(self, params:DuplicityParams):
        self.params = params

    def run_pre_backup(self) -> dict:
        """ Run pre backup processing. """
        return self.__write_duplicity_restore_test_file()

    def run_backup(self) -> dict:
        """ Run backup and return metrics. """
        logs = self.__capture_command_out(
            command=self.__build_duplicity_command(),
            print_prefix="[Duplicity Ouput]")
        return self.__process_duplicity_logs(logs)

    def __build_duplicity_command(self) -> list:
        """ Build the duplicity command. """
        out = ["duplicity"]
        if self.params.full_if_older_than:
            out.append("--full-if-older-than=" + self.params.full_if_older_than)
        if self.params.verbosity:
            out.append("--verbosity=" + self.params.verbosity)
        if self.params.allow_source_mismatch:
            out.append("--allow-source-mismatch")
        if self.params.backup_method == DuplicityBackupMethod.SSH:
            ssh_options = "--rsync-options='-e \"ssh "
            ssh_options += " -p " + self.params.ssh_params.port
            ssh_options += " -i " + self.params.ssh_params.key_file
            if self.params.ssh_params.strict_host_key_checking:
                ssh_options += " -o StrictHostKeyChecking=yes"
            else:
                ssh_options += " -o StrictHostKeyChecking=no"
            ssh_options += "\"'"
            out.append(ssh_options)
        out.append(" /home/duplicity/backup/data")
        if self.params.backup_method == DuplicityBackupMethod.SSH:
            rsync_location = "rsync://"
            rsync_location += self.params.ssh_params.user
            rsync_location += "@"
            rsync_location += self.params.ssh_params.host
            rsync_location += ":"
            rsync_location += self.params.location_params.remote_path
            out.append(rsync_location)
        return out

    def __build_duplicity_restore_test_command(self) -> list:
        """ Build the duplicity restore test command. """
        out = ["duplicity"]
        out.append("--allow-source-mismatch")
        out.append("--force")
        out.append("--file-to-restore="+self.params.location_params.pre_backup_date_file)
        if self.params.verbosity:
            out.append("--verbosity=" + self.params.verbosity)
        if self.params.backup_method == DuplicityBackupMethod.SSH:
            ssh_options = "--rsync-options='-e \"ssh "
            ssh_options += " -p " + self.params.ssh_params.port
            ssh_options += " -i " + self.params.ssh_params.key_file
            if self.params.ssh_params.strict_host_key_checking:
                ssh_options += " -o StrictHostKeyChecking=yes"
            else:
                ssh_options += " -o StrictHostKeyChecking=no"
            ssh_options += "\"'"
            out.append(ssh_options)
        out.append(" /home/duplicity/backup/data")
        if self.params.backup_method == DuplicityBackupMethod.SSH:
            rsync_location = "rsync://"
            rsync_location += self.params.ssh_params.user
            rsync_location += "@"
            rsync_location += self.params.ssh_params.host
            rsync_location += ":"
            rsync_location += self.params.location_params.remote_path
            out.append(rsync_location)
        out.append(self.params.location_params.restored_date_file)
        return out

    def run_post_backup(self):
        """ Run post backup processing. """
        self.__capture_command_out(
            command=self.__build_duplicity_restore_test_command(),
            print_prefix="[Duplicity Restore Test Ouput]")
        return self.__read_duplicity_restore_test_file()

    def __capture_command_out(self, command:list, print_prefix="") -> list:
        """ Runs a command on the command line and returns output. """
        if str(os.getenv("PASSPHRASE", "")) == "":
            raise Exception("PASSPHRASE not set!")
        if print_prefix:
            print(print_prefix + "[Command]: " + " ".join(command))
        my_env = os.environ.copy()
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=my_env
            )
        out = []
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            if print_prefix:
                print(print_prefix + ": " + line.decode('utf-8'))
            out.append(line.decode('utf-8'))
        return out

    def __process_duplicity_logs(self, log_output:list) -> dict:
        """ Process duplicity logs to extract metrics. """
        out = copy.deepcopy(metric_template)

        reached_stats = False
        for line in log_output:
            if reached_stats:
                if line.startswith("-------------------------------------------------"):
                    out["getSuccess"] = True
                else:
                    sline = line.split(" ")
                    if len(sline) > 1:
                        match sline[0]:
                            case "StartTime":
                                out["lastBackup"] = int(float(sline[1]))
                            case "ElapsedTime":
                                out["elapseTime"] = int(float(sline[1]))
                            case "Errors":
                                out["errors"] = sline[1]
                            case "NewFiles":
                                out["files"]["new"] = sline[1]
                            case "DeletedFiles":
                                out["files"]["deleted"] = sline[1]
                            case "ChangedFiles":
                                out["files"]["changed"] = sline[1]
                            case "DeltaEntries":
                                out["files"]["delta"] = sline[1]
                            case "RawDeltaSize":
                                out["size"]["rawDelta"] = sline[1]
                            case "ChangedFileSize":
                                out["size"]["changedFiles"] = sline[1]
                            case "SourceFileSize":
                                out["size"]["sourceFile"] = sline[1]
                            case "TotalDestinationSizeChange":
                                out["size"]["totalDestChange"] = sline[1]
            elif line.startswith("--------------[ Backup Statistics ]--------------"):
                reached_stats = True

        out["timeSinceBackup"] = int(float(time.time()) - float(out["lastBackup"]))

        return out

    def __write_duplicity_restore_test_file(self) -> dict:
        """ Write a date file to check restore works correctly. """
        out = {
            "backup-test-file-date": 0,
            "backup-test-file-success": False,
        }
        pre_backup_date_file = self.params.location_params.local_backup_path
        pre_backup_date_file += "/" + self.params.location_params.pre_backup_date_file
        self.__capture_command_out(['date', '>', pre_backup_date_file])

        out_temp = self.__read_date_file(pre_backup_date_file)
        out["restore-file-read-success"] = out_temp[0]
        out["restore-file-date"] = out_temp[1]

        return out

    def __read_duplicity_restore_test_file(self) -> dict:
        """ Read a restore date file test file. """
        out = {
            "restore-file-date": 0,
            "restore-file-read-success": False
        }
        out_temp = self.__read_date_file(self.params.location_params.restored_date_file)
        out["restore-file-read-success"] = out_temp[0]
        out["restore-file-date"] = out_temp[1]

    def __read_date_file(self, location:str) -> (bool, int):
        """ Read and process a date file. """
        try:
            restored_test_file = self.__capture_command_out(['cat', location])
            restored_test_file_content = "".join(restored_test_file).replace("\n","")
            return True, self.__process_date_file(restored_test_file_content)
        except Exception as e:
            print("Caught Error While Processing Restore Date File: " + str(e))
        return False, 0

    def __process_date_file(self, file_content:str)  -> int:
        """ Process date file. """
        return int(datetime.strptime(file_content, "%a %d %b %H:%M:%S %Z %Y").timestamp())
