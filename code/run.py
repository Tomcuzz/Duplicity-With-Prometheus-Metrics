"""Application exporter"""

from dataclasses import dataclass

import os
import time
import json
from prometheus_client import start_http_server, Gauge, Enum
import duplicity

#24 hours
ONE_DAY = "86400"

@dataclass
class AppMetricParams:
    """ Needed Setup params for AppMetrics. """
    duplicity_params:duplicity.DuplicityParams = duplicity.DuplicityParams()
    last_metric_location:str
    backup_interval:int

@dataclass
class Metrics:
    """Class to hold prometheus Metrics."""
    got_metrics = Enum(
        "duplicity_got_metrics", "Able to get metrics",
        states=["True", "False"], labelnames=['backup_name'])
    last_backup =  Gauge(
        "duplicity_last_backup", "Last Backup Date", labelnames=['backup_name'])
    elapse_time =  Gauge(
        "duplicity_elapse_time", "Backup Elapse Time", labelnames=['backup_name'])
    time_since_backup =  Gauge(
        "duplicity_time_since_backup", "Time Since Last Backup", labelnames=['backup_name'])
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
        self.backup_name = params.backup_name
        self.last_metric_location = params.last_metric_location
        self.pre_backup_date_file = params.pre_backup_date_file
        self.restored_date_file = params.restored_date_file
        self.backup_interval = params.backup_interval
        print("Adding Metrics")
        # duplicity_location_params = duplicity.DuplicityLocationParams(
        #     pre_backup_date_file=params.pre_backup_date_file,
        #     restored_date_file=params.restored_date_file
        # )
        duplicity_params = duplicity.DuplicityParams(
            backup_name=params.backup_name,
            pre_backup_date_file=params.pre_backup_date_file,
            restored_date_file=params.restored_date_file
            # location_params=duplicity_location_params
        )
        self.duplicity = duplicity.Duplicity(params=duplicity_params)
        self.last_run_metrics = {}
        self.metrics = Metrics()

    def pre_start_load(self):
        """Pre-Start metric load"""
        with open(self.last_metric_location, encoding="utf-8") as fp:
            self.last_run_metrics = json.load(fp)


    def run_metric_save(self):
        """Save metrics out to disk for container restart"""
         # Update Prometheus metrics with application metrics
        self.metrics.got_metrics.labels(
            container_name=self.backup_name).state(str(self.last_run_metrics["getSuccess"]))
        if self.last_run_metrics["getSuccess"]:
            self.metrics.last_backup.labels(
                container_name=self.backup_name).set(self.last_run_metrics["lastBackup"])
            self.metrics.time_since_backup.labels(
                container_name=self.backup_name).set(self.last_run_metrics["timeSinceBackup"])
            self.metrics.errors.labels(
                container_name=self.backup_name).set(self.last_run_metrics["errors"])
            self.metrics.new_files.labels(
                container_name=self.backup_name).set(self.last_run_metrics["files"]["new"])
            self.metrics.deleted_files.labels(
                container_name=self.backup_name).set(self.last_run_metrics["files"]["deleted"])
            self.metrics.changed_files.labels(
                container_name=self.backup_name).set(self.last_run_metrics["files"]["changed"])
            self.metrics.delta_entries.labels(
                container_name=self.backup_name).set(self.last_run_metrics["files"]["delta"])
            self.metrics.raw_delta_size.labels(
                container_name=self.backup_name).set(self.last_run_metrics["size"]["rawDelta"])
            self.metrics.changed_file_size.labels(
                container_name=self.backup_name).set(self.last_run_metrics["size"]["changedFiles"])
            self.metrics.source_file_size.labels(
                container_name=self.backup_name).set(self.last_run_metrics["size"]["sourceFile"])
            self.metrics.total_destination_size_change.labels(
                container_name=self.backup_name).set(
                    self.last_run_metrics["size"]["totalDestChange"])

        if self.last_run_metrics["backup-test-file-success"]:
            self.metrics.pre_backup_date_file_last_backup.labels(
                container_name=self.backup_name).set(self.last_run_metrics["backup-test-file-date"])
        if self.last_run_metrics["restore-file-read-success"]:
            self.metrics.restored_date_file_last_restore_date.labels(
                container_name=self.backup_name).set(self.last_run_metrics["restore-file-date"])
        with open(self.last_metric_location, 'w', encoding="utf-8") as fp:
            json.dump(self.last_run_metrics, fp)


    def run_loop(self):
        """Backup fetching loop"""
        while True:
            time.sleep(30)
            self.process_pre_backup_date_write()
            time.sleep(10)
            self.process_backup()
            time.sleep(10)
            self.process_post_backup_date_read()
            time.sleep(self.backup_interval)

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

    if str(os.getenv("DUPLICITY_SERVER_SSH_KEY_SSH_KEY", "")) != "":
        f = open(str(os.getenv("DUPLICITY_SERVER_SSH_KEY_FILE", "/home/duplicity/config/id_rsa")), "a")
        f.write(str(os.getenv("DUPLICITY_SERVER_SSH_KEY_SSH_KEY", "")))
        f.close()

    duplicity_connection_type = duplicity.DuplicityBackupMethod.UNKNOWN
    connection_env = str(os.getenv("DUPLICITY_SERVER_CONNECTION_TYPE", "ssh")).lower()
    if connection_env == "ssh":
        duplicity_connection_type = duplicity.DuplicityBackupMethod.SSH

    ssh_params = duplicity.SSHParams(
        host=str(os.getenv("DUPLICITY_SERVER_SSH_HOST", "192.168.1.1")),
        port=int(os.getenv("DUPLICITY_SERVER_SSH_PORT", "22")),
        user=str(os.getenv("DUPLICITY_SERVER_SSH_USER", "duplicity")),
        key_file=str(os.getenv("DUPLICITY_SERVER_SSH_KEY_FILE", "/home/duplicity/config/id_rsa"))
    )
    ssh_params.strict_host_key_checking = (
        str(os.getenv("DUPLICITY_SERVER_SSH_STRICT_HOST_KEY_CHECKING", "False")) == "False")

    # duplicity_location_params = duplicity.DuplicityLocationParams(
    #     local_backup_path = "/home/duplicity/backup",
    #     pre_backup_date_file=str(
    #         os.getenv("DATE_FILE_PRE_BACKUP", "restore_test.txt")),
    #     restored_date_file=str(
    #         os.getenv("DATE_FILE_RESTORED", "/home/duplicity/config/restore_test.txt")),
    #     remote_path = str(
    #         os.getenv("DUPLICITY_SERVER_REMOTE_PATH", "/home/duplicity/backup"))
    # )
    duplicity_params = duplicity.DuplicityParams(
        backup_name=str(os.getenv("BACKUP_NAME", "duplicity_backup")),
        full_if_older_than=str(os.getenv("DUPLICITY_FULL_IF_OLDER_THAN", "")),
        verbosity=str(os.getenv("DUPLICITY_VERBOSITY", "")),
        local_backup_path = "/home/duplicity/backup",
        pre_backup_date_file=str(
            os.getenv("DATE_FILE_PRE_BACKUP", "restore_test.txt")),
        restored_date_file=str(
            os.getenv("DATE_FILE_RESTORED", "/home/duplicity/config/restore_test.txt")),
        remote_path = str(
            os.getenv("DUPLICITY_SERVER_REMOTE_PATH", "/home/duplicity/backup")),
        # location_params=duplicity_location_params,
        backup_method=duplicity_connection_type,
        allow_source_mismatch=(str(os.getenv("DUPLICITY_ALLOW_SOURCE_MISMATCH", "True")) == "True"),
        ssh_params=ssh_params
    )
    app_metrics_params = AppMetricParams(
        duplicity_params = duplicity_params,
        last_metric_location = str(
            os.getenv("LAST_METRIC_LOCATION", "/home/duplicity/config/last_metrics")),
        backup_interval = int(os.getenv("BACKUP_INTERVAL", ONE_DAY))
    )
    app_metrics = AppMetrics(
        params=app_metrics_params
    )

    print("Running pre-run load")
    app_metrics.pre_start_load()

    start_http_server(exporter_port)
    print("Started")
    app_metrics.run_loop()

if __name__ == "__main__":
    main()
