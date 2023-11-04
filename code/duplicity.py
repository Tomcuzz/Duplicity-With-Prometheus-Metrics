"""Duplicity healper"""

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

class Duplicity:
    """ Class to handle Duplicity commands. """
    def __init__(
            self,
            backup_name="duplicity",
            pre_backup_date_file="",
            restored_date_file="",
            duplicity_full_if_older_than="",
            duplicity_verbosity="",
            duplicity_allow_source_mismatch=True,
            duplicity_backup_method="ssh",
            duplicity_ssh_port=22,
            duplicity_ssh_key_file="/id_rsa",
            duplicity_ssh_user="duplicity",
            duplicity_ssh_host="192.168.1.1",
            duplicity_remote_path="/home/duplicity/backup",
            duplicity_ssh_strict_host_key_checking=False):
        self.backup_name = backup_name
        self.pre_backup_date_file = pre_backup_date_file
        self.restored_date_file = restored_date_file
        self.duplicity_full_if_older_than = duplicity_full_if_older_than
        self.duplicity_verbosity = duplicity_verbosity
        self.duplicity_allow_source_mismatch = duplicity_allow_source_mismatch
        self.duplicity_backup_method = duplicity_backup_method
        self.duplicity_ssh_port = duplicity_ssh_port
        self.duplicity_ssh_key_file = duplicity_ssh_key_file
        self.duplicity_ssh_user = duplicity_ssh_user
        self.duplicity_ssh_host = duplicity_ssh_host
        self.duplicity_remote_path = duplicity_remote_path
        self.duplicity_ssh_strict_host_key_checking = duplicity_ssh_strict_host_key_checking

    def run_pre_backup(self) -> dict:
        """ Run pre backup processing. """
        return self.__write_duplicity_restore_test_file()

    def run_backup(self) -> dict:
        """ Run backup and return metrics. """
        logs = self.__capture_command_out(
            command=self.__build_duplicity_command(),
            print_output=True)
        return self.__process_duplicity_logs(logs)

    def __build_duplicity_command(self) -> list:
        """ Build the duplicity command. """
        out = ["duplicity"]
        if self.duplicity_full_if_older_than:
            out.append("--full-if-older-than=" + self.duplicity_full_if_older_than)
        if self.duplicity_verbosity:
            out.append("--verbosity=" + self.duplicity_verbosity)
        if self.duplicity_allow_source_mismatch:
            out.append("--allow-source-mismatch")
        if self.duplicity_backup_method == "ssh":
            ssh_options = "--rsync-options='-e \"ssh "
            ssh_options += " -p " + self.duplicity_ssh_port
            ssh_options += " -i " + self.duplicity_ssh_key_file
            if self.duplicity_ssh_strict_host_key_checking:
                ssh_options += " -o StrictHostKeyChecking=yes"
            else:
                ssh_options += " -o StrictHostKeyChecking=no"
            ssh_options += "\"'"
            out.append(ssh_options)
        out.append(" /home/duplicity/backup/data")
        if self.duplicity_backup_method == "ssh":
            rsync_location = "rsync://"
            rsync_location += self.duplicity_ssh_user
            rsync_location += "@"
            rsync_location += self.duplicity_ssh_host
            rsync_location += ":"
            rsync_location += self.duplicity_remote_path
            out.append(rsync_location)
        return out

    def run_post_backup(self):
        """ Run post backup processing. """
        return self.__read_duplicity_restore_test_file()

    def __capture_command_out(self, command:list, print_output=False) -> list:
        """ Runs a command on the command line and returns output. """
        proc = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out = []
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            if print_output:
                print("[Duplicity Ouput]: " + line.decode('utf-8'))
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
        self.__capture_command_out(['date', '>', self.pre_backup_date_file])

        out_temp = self.__read_date_file(self.pre_backup_date_file)
        out["restore-file-read-success"] = out_temp[0]
        out["restore-file-date"] = out_temp[1]

        return out

    def __read_duplicity_restore_test_file(self) -> dict:
        """ Read a restore date file test file. """
        out = {
            "restore-file-date": 0,
            "restore-file-read-success": False
        }
        out_temp = self.__read_date_file(self.restored_date_file)
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
