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
            restored_date_file=""):
        self.backup_name = backup_name
        self.pre_backup_date_file = pre_backup_date_file
        self.restored_date_file = restored_date_file

    def run_pre_backup(self):
        """ Run pre backup processing. """
        return self.__write_duplicity_restore_test_file()

    def run_backup(self):
        """ Run backup and return metrics. """
        logs = self.__capture_command_out(
            command=[''], # command=['docker', 'logs', self.backup_name, "-n", "40"],
            print_output=True)
        return self.__process_duplicity_logs(logs)

    def run_post_backup(self):
        """ Run post backup processing. """
        return self.__read_duplicity_restore_test_file()

    def __capture_command_out(self, command, print_output=False):
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

    def __process_duplicity_logs(self, log_output):
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

    def __write_duplicity_restore_test_file(self):
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

    def __read_duplicity_restore_test_file(self):
        """ Read a restore date file test file. """
        out = {
            "restore-file-date": 0,
            "restore-file-read-success": False
        }
        out_temp = self.__read_date_file(self.restored_date_file)
        out["restore-file-read-success"] = out_temp[0]
        out["restore-file-date"] = out_temp[1]

    def __read_date_file(self, location):
        """ Read and process a date file. """
        try:
            restored_test_file = self.__capture_command_out(['cat', location])
            restored_test_file_content = "".join(restored_test_file).replace("\n","")
            return True, self.__process_date_file(restored_test_file_content)
        except Exception as e:
            print("Caught Error While Processing Restore Date File: " + str(e))
        return False, 0

    def __process_date_file(self, file_content):
        """ Process date file. """
        return int(datetime.strptime(file_content, "%a %d %b %H:%M:%S %Z %Y").timestamp())
