"""Application exporter"""

from dataclasses import dataclass, field

import os
import stat
import copy
import time
import json
from prometheus_client import start_http_server, Gauge, Enum
import duplicity

#24 hours
ONE_DAY = "86400"

@dataclass
class AppMetricParams:
    """ Needed Setup params for AppMetrics. """
    last_metric_location:str
    backup_interval:int
    backup_name:str = "duplicity"
    duplicity_params:duplicity.DuplicityParams = field(default_factory=duplicity.DuplicityParams)

@dataclass
class Metrics:
    """Class to hold prometheus Metrics."""
    backup_state = Enum(
        "duplicity_backup_state", "The current job state",
        states=["Unkown", "Running", "Waiting", "Cleaning Up"], labelnames=['backup_name'])
    got_metrics = Enum(
        "duplicity_got_metrics", "Able to get metrics",
        states=["True", "False"], labelnames=['backup_name'])
    last_backup =  Gauge(
        "duplicity_last_backup", "Last Backup Date", labelnames=['backup_name'])
    next_backup =  Gauge(
        "duplicity_next_backup", "Next Backup Date", labelnames=['backup_name'])
    elapse_time =  Gauge(
        "duplicity_elapse_time", "Backup Elapse Time", labelnames=['backup_name'])
    errors = Gauge(
        "duplicity_errors", "Backup Errors", labelnames=['backup_name'])
    new_files = Gauge(
        "duplicity_new_files", "Number Of New Files", labelnames=['backup_name'])
    deleted_files = Gauge(
        "duplicity_deleted_files", "Number Of Deleted Files", labelnames=['backup_name'])
    changed_files = Gauge(
        "duplicity_changed_files", "Number Of Changed Files", labelnames=['backup_name'])
    delta_entries = Gauge(
        "duplicity_delta_entries", "Delta Of Number Of Files", labelnames=['backup_name'])
    raw_delta_size = Gauge(
        "duplicity_raw_delta_size", "Raw Backup Size Delta", labelnames=['backup_name'])
    changed_file_size = Gauge(
        "duplicity_changed_file_size", "Sum Size Of Changed Files", labelnames=['backup_name'])
    source_file_size = Gauge(
        "duplicity_source_file_size", "", labelnames=['backup_name'])
    total_destination_size_change = Gauge(
        "duplicity_total_destination_size_change", "", labelnames=['backup_name'])

    num_full_backups = Gauge(
        "duplicity_num_full_backups", "Number of Full Backups on Target", labelnames=['backup_name'])
    num_incremental_backups = Gauge(
        "duplicity_num_incremental_backups", "Number of Incremental Backups on Target", labelnames=['backup_name'])

    local_folder_size = Gauge(
        "duplicity_local_folder_size", "Size of folder to be backed up", labelnames=['backup_name'])
    backup_folder_size = Gauge(
        "duplicity_backup_folder_size", "Size of backup folder", labelnames=['backup_name'])

    pre_backup_date_file_last_backup =  Gauge(
        "duplicity_pre_backup_date_file_date",
        "Last Pre Backup File Backup Date",
        labelnames=['backup_name'])
    restored_date_file_last_restore_date =  Gauge(
        "duplicity_restored_date_file_last_restore_date",
        "Last Restore File Date",
        labelnames=['backup_name'])


class AppMetrics:
    """
    Representation of Prometheus metrics and loop to backup and transform
    application metrics into Prometheus metrics.
    """

    def __init__(
            self,
            params:AppMetricParams):
        self.params = params
        print("Adding Metrics")
        self.last_run_metrics = {}
        self.metrics = Metrics()
        self.metrics.backup_state.labels(backup_name=self.params.backup_name).state("Unkown")
        self.duplicity = duplicity.Duplicity(params=params.duplicity_params)
        self.last_run_metrics = copy.deepcopy(duplicity.metric_template)

    def pre_start_load(self):
        """Pre-Start metric load"""
        try:
            with open(self.params.last_metric_location, encoding="utf-8") as fp:
                self.last_run_metrics = json.load(fp)
        except FileNotFoundError:
            print("No Previous Metrics Found")


    def run_metric_save(self):
        """Save metrics out to disk for container restart"""
        try:
            # Update Prometheus metrics with application metrics
            self.metrics.got_metrics.labels(
                backup_name=self.params.backup_name).state(str(self.last_run_metrics["getSuccess"]))
            if self.last_run_metrics["getSuccess"]:
                self.metrics.last_backup.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["lastBackup"])
                self.metrics.elapse_time.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["elapseTime"])
                self.metrics.errors.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["errors"])
                self.metrics.new_files.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["files"]["new"])
                self.metrics.deleted_files.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["files"]["deleted"])
                self.metrics.changed_files.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["files"]["changed"])
                self.metrics.delta_entries.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["files"]["delta"])
                self.metrics.raw_delta_size.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["size"]["rawDelta"])
                self.metrics.changed_file_size.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["size"]["changedFiles"])
                self.metrics.source_file_size.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["size"]["sourceFile"])
                self.metrics.total_destination_size_change.labels(
                    backup_name=self.params.backup_name).set(
                        self.last_run_metrics["size"]["totalDestChange"])

            if self.last_run_metrics["backup-test-file-success"]:
                self.metrics.pre_backup_date_file_last_backup.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["backup-test-file-date"])
            if self.last_run_metrics["restore-file-read-success"]:
                self.metrics.restored_date_file_last_restore_date.labels(
                    backup_name=self.params.backup_name).set(self.last_run_metrics["restore-file-date"])
            with open(self.params.last_metric_location, 'w+', encoding="utf-8") as fp:
                json.dump(self.last_run_metrics, fp)
        except KeyError:
            print("run_metric_save: Key Error")
        except ValueError:
            print("run_metric_save: Value Error")

    def save_last_collection_stats(self, output:dict):
        """Publish last collection stats"""
        try:
            self.metrics.num_full_backups.labels(
                backup_name=self.params.backup_name).set(output["fullBackups"]["num"])
            self.metrics.num_incremental_backups.labels(
                backup_name=self.params.backup_name).set(output["incrementalBackups"]["num"])
        except KeyError:
            print("run_metric_save: Key Error")
        except ValueError:
            print("run_metric_save: Value Error")
    
    def run_loop(self):
        """Backup fetching loop"""
        
        while True:
            self.run_collection_status()
            self.metrics.backup_state.labels(backup_name=self.params.backup_name).state("Running")
            self.run_collection_status()
            self.run_old_backup_clean()
            self.run_cleanup()
            self.run_collection_status()
            self.process_pre_backup_date_write()
            self.process_backup()
            self.process_post_backup_date_read()
            self.metrics.backup_state.labels(backup_name=self.params.backup_name).state("Cleaning Up")
            self.run_old_backup_clean()
            self.run_cleanup()
            self.metrics.next_backup.labels(backup_name=self.params.backup_name).set(
                int(float(time.time()) + self.params.backup_interval))
            self.metrics.backup_state.labels(backup_name=self.params.backup_name).state("Waiting")
            self.run_collection_status()
            time.sleep(self.params.backup_interval)

    def run_restore(self):
        """Run duplicity restore."""
        self.duplicity.run_restore()
        print("Restore Finished")
        while True:
            time.sleep(1000)

    def run_old_backup_clean(self):
        """Run duplicity old backup clean."""
        self.duplicity.run_old_backup_clean()

    def run_cleanup(self):
        """Run duplicity cleanup command."""
        self.duplicity.run_cleanup()

    def run_collection_status(self):
        """Run duplicity collection status."""
        self.save_last_collection_stats(self.duplicity.run_collection_status())
        self.metrics.local_folder_size.labels(backup_name=self.params.backup_name).set(
            self.duplicity.get_local_size())
        self.metrics.backup_folder_size.labels(backup_name=self.params.backup_name).set(
            self.duplicity.get_backup_size())

    def process_pre_backup_date_write(self):
        """Run pre-backup restore date file write and save/export metric."""
        self.last_run_metrics.update(self.duplicity.run_pre_backup())
        self.run_metric_save()

    def process_backup(self):
        """Run backup and save/export metric."""
        self.last_run_metrics.update(self.duplicity.run_backup())
        self.run_metric_save()

    def process_post_backup_date_read(self):
        """Run pre-backup restore date file write and save/export metric."""
        self.last_run_metrics.update(self.duplicity.run_post_backup())
        self.run_metric_save()

def main():
    """Main entry point"""

    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))

    print("Starting Exporter on port: " + str(exporter_port))

    if str(os.getenv("PASSPHRASE", "")) == "":
        raise Exception("PASSPHRASE not set!")

    duplicity_connection_type = duplicity.DuplicityBackupMethod.UNKNOWN
    connection_env = str(os.getenv("DUPLICITY_SERVER_CONNECTION_TYPE", "ssh")).lower()
    if connection_env == "ssh":
        duplicity_connection_type = duplicity.DuplicityBackupMethod.SSH
    elif connection_env == "local":
        duplicity_connection_type = duplicity.DuplicityBackupMethod.LOCAL

    ssh_key_string = str(os.getenv("DUPLICITY_SERVER_SSH_KEY_SSH_KEY", ""))
    ssh_key_blank = (ssh_key_string == "")
    ssh_key_path = str(os.getenv("DUPLICITY_SERVER_SSH_KEY_FILE", "/home/duplicity/config/id_rsa"))
    ssh_key_file_exists = os.path.isfile(ssh_key_path)
    
    if connection_env == "ssh" and ssh_key_blank and not ssh_key_file_exists:
        raise Exception("No ssh key provided!")

    if not ssh_key_blank:
        ssh_key_path_directory = os.path.abspath(os.path.join(ssh_key_path, os.pardir))
        if not os.path.exists(ssh_key_path_directory):
            os.makedirs(ssh_key_path_directory, exist_ok=True)
        f = open(ssh_key_path, "w+")
        f.write(str(os.getenv("DUPLICITY_SERVER_SSH_KEY_SSH_KEY", "")) + "\n")
        f.close()
        os.chmod(
            ssh_key_path,
            stat.S_IRUSR |
            stat.S_IWUSR
        )

    ssh_params = duplicity.SSHParams(
        host=str(os.getenv("DUPLICITY_SERVER_SSH_HOST", "192.168.1.1")),
        port=int(os.getenv("DUPLICITY_SERVER_SSH_PORT", "22")),
        user=str(os.getenv("DUPLICITY_SERVER_SSH_USER", "duplicity")),
        key_file=ssh_key_path
    )
    ssh_params.strict_host_key_checking = (
        str(os.getenv("DUPLICITY_SERVER_SSH_STRICT_HOST_KEY_CHECKING", "False")) == "True")

    if duplicity_connection_type == duplicity.DuplicityBackupMethod.SSH:
        if not os.path.exists("/home/duplicity/.ssh"):
            os.makedirs("/home/duplicity/.ssh", exist_ok=True)
        with open("/home/duplicity/.ssh/config", "w+", encoding="utf-8") as fp:
                fp.write("Host " + ssh_params.host + "\r\n")
                fp.write("  HostName " + ssh_params.host + "\r\n")
                fp.write("  Port " + str(ssh_params.port) + "\r\n")
                fp.write("  User " + ssh_params.user + "\r\n")
                fp.write("  IdentityFile " + ssh_params.key_file + "\r\n")
                if ssh_params.strict_host_key_checking:
                    fp.write("  StrictHostKeyChecking yes\r\n")
                else:
                    fp.write("  StrictHostKeyChecking no\r\n")

    duplicity_location_params = duplicity.DuplicityLocationParams(
        local_backup_path = "/backup",
        pre_backup_date_file=str(
            os.getenv("DATE_FILE_PRE_BACKUP", "restore_test.txt")),
        restored_date_file=str(
            os.getenv("DATE_FILE_RESTORED", "/home/duplicity/config/restore_test.txt")),
        remote_path = str(
            os.getenv("DUPLICITY_SERVER_REMOTE_PATH", "/home/duplicity/backup"))
    )
    duplicity_params = duplicity.DuplicityParams(
        full_if_older_than=str(os.getenv("DUPLICITY_FULL_IF_OLDER_THAN", "")),
        remove_all_but_n_full=int(os.getenv("DUPLICITY_REMOVE_ALL_BUT_N_FULL", 0)),
        remove_all_inc_of_but_n_full=int(os.getenv("DUPLICITY_REMOVE_ALL_INC_OF_BUT_N_FULL", 0)),
        exclude_backup_dirs=str(os.getenv("EXCLUDE_BACKUP_DIRS", "")),
        restore_to_time=str(os.getenv("RESTORE_TO_TIME", "")),
        verbosity=str(os.getenv("DUPLICITY_VERBOSITY", "")),
        location_params=duplicity_location_params,
        backup_method=duplicity_connection_type,
        allow_source_mismatch=(str(os.getenv("DUPLICITY_ALLOW_SOURCE_MISMATCH", "True")) == "True"),
        ssh_params=ssh_params
    )

    app_metrics_params = AppMetricParams(
        backup_name=str(os.getenv("BACKUP_NAME", "duplicity_backup")),
        duplicity_params = duplicity_params,
        last_metric_location = str(
            os.getenv("LAST_METRIC_LOCATION", "/home/duplicity/config/last_metrics")),
        backup_interval = int(os.getenv("BACKUP_INTERVAL", ONE_DAY))
    )
    app_metrics = AppMetrics(
        params=app_metrics_params
    )

    duplicity_run_mode = str(os.getenv("DUPLICITY_RUN_MODE", "BACKUP"))
    if duplicity_run_mode == "RESTORE":
        print("Starting Restore")
        app_metrics.run_restore()
        return
    
    if duplicity_run_mode == "CLEAN":
        print("Starting Clean")
        app_metrics.run_old_backup_clean()
        print("Clean Finished")
        while True:
            time.sleep(1000)

    if duplicity_run_mode == "CLEANUP":
        print("Starting Cleanup")
        app_metrics.run_cleanup()
        print("Cleanup Finished")
        while True:
            time.sleep(1000)

    if duplicity_run_mode == "COLLECTION-STATS":
        print("Starting collection status")
        app_metrics.run_collection_status()
        print("collection status Finished")
        while True:
            time.sleep(1000)

    if duplicity_run_mode == "WAIT":
        print("Going into wait mode")
        while True:
            time.sleep(5)

    print("Running pre-run load")
    app_metrics.pre_start_load()

    start_http_server(exporter_port)
    print("Started")
    app_metrics.run_loop()

if __name__ == "__main__":
    main()
