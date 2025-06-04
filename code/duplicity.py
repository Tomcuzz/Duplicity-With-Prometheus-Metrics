"""Duplicity healper"""

from dataclasses import dataclass, field
from enum import Enum

import os
import copy
import time
import subprocess

import pytz
from datetime import datetime

metric_template = {
    "running":              False,
    "getSuccess":           False,
    "lastBackup":           0,
    "elapseTime":           0,
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

collection_status_metrics_template = {
    "fullBackups": {
        "num":                0
    },
    "incrementalBackups": {
        "num":                0
    }
}

class DuplicityBackupMethod(Enum):
    """An enum to control backup storage location connection type."""
    UNKNOWN = 0
    SSH = 1
    LOCAL = 2


@dataclass
class SSHParams():
    """Setup params for ssh params."""
    port:int = 22
    key_file:str = "/home/duplicity/config/id_rsa"
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
    local_path:str = "/backup"
    restore_confirm_file_path:str = "/backup/data/restore_confirm"


@dataclass
class DuplicityParams:
    """Setup params for dupliciy class."""
    location_params:DuplicityLocationParams = field(default_factory=DuplicityLocationParams)
    full_if_older_than:str = ""
    remove_all_but_n_full:int = 0
    exclude_backup_dirs:str = ""
    restore_to_time:str = ""
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

    def run_collection_status(self) -> dict:
        """ Run duplicity cleanup. """
        print("[Duplicity Collection Status]: Starting Collection Status")
        log = self.__capture_command_out(
            command=self.__build_duplicity_collection_status_command(),
            print_prefix="[Duplicity Collection Status]")
        return self.__process_duplicity_collection_status(log)

    def run_cleanup(self) -> dict:
        """ Run duplicity cleanup. """
        print("[Duplicity Cleanup]: Starting old backup clean")
        log = self.__capture_command_out(
            command=self.__build_duplicity_cleanup_command(),
            print_prefix="[Duplicity Cleanup]")
        return {"sucess": True}

    def run_old_backup_clean(self) -> dict:
        """ Run cleanup of old backups. """
        if self.params.remove_all_but_n_full > 0:
            print("[Duplicity Old Backup Cleanup]: Starting old backup clean")
            log = self.__capture_command_out(
                command=self.__build_duplicity_old_backup_clean_command(),
                print_prefix="[Duplicity Backup Old Cleanup]")
        else:
            print("[Duplicity Backup Old Cleanup]: 0 \"remove_all_but_n_full\" given so clean was not run")
        return {"sucess": True}

    def run_restore(self) -> bool:
        """ Run restore and return success. """
        if self.__check_restore_confirmation_file():
            self.__capture_command_out(
                command=self.__build_duplicity_restore_command(),
                print_prefix="[Duplicity Restore Ouput]")
            restore_time = self.__write_restore_confirmation_file_completion()
            print(
                "[Duplicity Restore Ouput]: Restore complete with output time: "
                + restore_time)
            return True
        else:
            print("Error restore confirmation file not present and correct")
        return False

    def __build_duplicity_command(self) -> list:
        """ Build the duplicity command. """
        out = ["duplicity"]
        out.append("--allow-source-mismatch")
        if self.params.full_if_older_than:
            out.append("--full-if-older-than=" + self.params.full_if_older_than)
        if self.params.verbosity:
            out.append("--verbosity=" + self.params.verbosity)
        if self.params.exclude_backup_dirs:
            for exclude_dir in self.params.exclude_backup_dirs.split(","):
                out.append("--exclude=" + exclude_dir)
        out.append("--exclude=/backup/data/lost+found")
        out.append(self.params.location_params.local_path)
        if self.params.backup_method == DuplicityBackupMethod.SSH:
            rsync_location = "rsync://"
            rsync_location += self.params.ssh_params.user
            rsync_location += "@"
            rsync_location += self.params.ssh_params.host
            rsync_location += "/"
            rsync_location += self.params.location_params.remote_path
            out.append(rsync_location)
        elif self.params.backup_method == DuplicityBackupMethod.LOCAL:
            out.append("file://" + self.params.location_params.remote_path)
        return out

    def __build_duplicity_cleanup_command(self) -> list:
        """ Build the duplicity command. """
        out = ["duplicity", "cleanup"]
        out.append("--allow-source-mismatch")
        out.append("--force") # Use force to actually delete rather than just list
        if self.params.verbosity:
            out.append("--verbosity=" + self.params.verbosity)
        if self.params.backup_method == DuplicityBackupMethod.SSH:
            rsync_location = "rsync://"
            rsync_location += self.params.ssh_params.user
            rsync_location += "@"
            rsync_location += self.params.ssh_params.host
            rsync_location += "/"
            rsync_location += self.params.location_params.remote_path
            out.append(rsync_location)
        elif self.params.backup_method == DuplicityBackupMethod.LOCAL:
            out.append("file://" + self.params.location_params.remote_path)
        return out

    def __build_duplicity_collection_status_command(self) -> list:
        """ Build the duplicity command. """
        out = ["duplicity", "collection-status"]
        out.append("--allow-source-mismatch")
        out.append("--force") # Use force to actually delete rather than just list
        if self.params.verbosity:
            out.append("--verbosity=" + self.params.verbosity)
        if self.params.backup_method == DuplicityBackupMethod.SSH:
            rsync_location = "rsync://"
            rsync_location += self.params.ssh_params.user
            rsync_location += "@"
            rsync_location += self.params.ssh_params.host
            rsync_location += "/"
            rsync_location += self.params.location_params.remote_path
            out.append(rsync_location)
        elif self.params.backup_method == DuplicityBackupMethod.LOCAL:
            out.append("file://" + self.params.location_params.remote_path)
        return out
    
    def __build_duplicity_old_backup_clean_command(self) -> list:
        """ Build the duplicity command. """
        out = ["duplicity", "remove-all-but-n-full"]
        out.append(str(self.params.remove_all_but_n_full))
        out.append("--allow-source-mismatch")
        out.append("--force") # Use force to actually delete rather than just list
        if self.params.verbosity:
            out.append("--verbosity=" + self.params.verbosity)
        if self.params.backup_method == DuplicityBackupMethod.SSH:
            rsync_location = "rsync://"
            rsync_location += self.params.ssh_params.user
            rsync_location += "@"
            rsync_location += self.params.ssh_params.host
            rsync_location += "/"
            rsync_location += self.params.location_params.remote_path
            out.append(rsync_location)
        elif self.params.backup_method == DuplicityBackupMethod.LOCAL:
            out.append("file://" + self.params.location_params.remote_path)
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
            rsync_location = "rsync://"
            rsync_location += self.params.ssh_params.user
            rsync_location += "@"
            rsync_location += self.params.ssh_params.host
            rsync_location += "/"
            rsync_location += self.params.location_params.remote_path
            out.append(rsync_location)
        elif self.params.backup_method == DuplicityBackupMethod.LOCAL:
            out.append("file://" + self.params.location_params.remote_path)
        out.append(self.params.location_params.restored_date_file)
        return out

    def __build_duplicity_restore_command(self) -> list:
        """ Build the duplicity restore command. """
        out = ["duplicity", "restore"]
        out.append("--allow-source-mismatch")
        out.append("--force")
        out.append("--file-to-restore=data")
        if self.params.verbosity:
            out.append("--verbosity=" + self.params.verbosity)
        if self.params.restore_to_time:
            out.append("--restore-time=" + self.params.restore_to_time)
        if self.params.backup_method == DuplicityBackupMethod.SSH:
            rsync_location = "rsync://"
            rsync_location += self.params.ssh_params.user
            rsync_location += "@"
            rsync_location += self.params.ssh_params.host
            rsync_location += "/"
            rsync_location += self.params.location_params.remote_path
            out.append(rsync_location)
        elif self.params.backup_method == DuplicityBackupMethod.LOCAL:
            out.append("file://" + self.params.location_params.remote_path)
        out.append(self.params.location_params.local_path + "/data")
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
                print(print_prefix + ": " + line.decode('utf-8').strip())
            out.append(line.decode('utf-8'))
        while True:
            line = proc.stderr.readline()
            if not line:
                break
            print(print_prefix + "[COMMAND ERROR]" + ": " + line.decode('utf-8').strip())
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
        return out

    def __process_duplicity_collection_status(self, log_output:list) -> dict:
        """ Process duplicity collection status to extract metrics. """
        out = copy.deepcopy(collection_status_metrics_template)
        reached_stats = False
        for line in log_output:
            if reached_stats:
                if line.startswith("Full   "):
                    out["fullBackups"]["num"] += 1
                elif line.startswith("Incremental   "):
                    out["incrementalBackups"]["num"] += 1
            elif line.replace(" ", "").startswith("Collection Status"):
                reached_stats = True
        return out

    def __write_duplicity_restore_test_file(self) -> dict:
        """ Write a date file to check restore works correctly. """
        out = {
            "backup-test-file-date": 0,
            "backup-test-file-success": False,
        }
        pre_backup_date_file = self.params.location_params.local_backup_path
        if not os.path.exists(pre_backup_date_file):
            os.makedirs(pre_backup_date_file)

        pre_backup_date_file += "/" + self.params.location_params.pre_backup_date_file
        with open(pre_backup_date_file, "w+", encoding="utf-8") as fp:
            fp.write(datetime.now(pytz.utc).strftime("%a %d %b %H:%M:%S %Z %Y"))

        out_temp = self.__read_date_file(pre_backup_date_file)
        out["backup-test-file-success"] = out_temp[0]
        out["backup-test-file-date"] = out_temp[1]
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
        return out

    def __read_date_file(self, location:str) -> (bool, int):
        """ Read and process a date file. """
        try:
            with open(location) as f:
                restored_test_file = f.read()
                restored_test_file_content = "".join(restored_test_file).replace("\n","")
                return True, self.__process_date_file(restored_test_file_content)
        except Exception as e:
            print("Caught Error While Processing Restore Date File: " + str(e))
        return False, 0

    def __check_restore_confirmation_file(self) -> bool:
        """ Read restore confirmation file and return if ok to restore. """
        try:
            with open(self.params.location_params.restore_confirm_file_path, encoding="utf-8") as f:
                restore_confirm_file = f.read()
                restore_confirm_file_content = "".join(restore_confirm_file).replace("\n","")
                if restore_confirm_file_content == "restore":
                    return True
        except Exception as e:
            print("Caught Error While Processing Restore Confirm File: " + str(e))
        return False

    def __write_restore_confirmation_file_completion(self) -> str:
        restore_time = datetime.now(pytz.utc).strftime("%a %d %b %H:%M:%S %Z %Y")
        with open(self.params.location_params.restore_confirm_file_path, "w+", encoding="utf-8") as fp:
            fp.write("Restore complete: " + restore_time)
        return restore_time

    def __process_date_file(self, file_content:str)  -> int:
        """ Process date file. """
        return int(datetime.strptime(file_content, "%a %d %b %H:%M:%S %Z %Y").timestamp())
