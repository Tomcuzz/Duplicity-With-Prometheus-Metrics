"""Application exporter"""

import os
import time
import json
from prometheus_client import start_http_server, Gauge, Enum
import duplicity

#24 hours
ONE_DAY = "86400"

class AppMetrics:
    """
    Representation of Prometheus metrics and loop to backup and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, backup_name, last_metric_location, pre_backup_date_file, restored_date_file, backup_interval):
        self.backup_name = backup_name
        self.last_metric_location = last_metric_location
        self.pre_backup_date_file = pre_backup_date_file
        self.restored_date_file = restored_date_file
        self.backup_interval = backup_interval
        print("Adding Metrics")
        self.duplicity = duplicity.Duplicity(
            backup_name=backup_name,
            pre_backup_date_file=pre_backup_date_file,
            restored_date_file=restored_date_file
        )
        self.last_run_metrics = {}

        # Prometheus metrics to collect
        self.got_metrics = Enum("duplicity_got_metrics", "Able to get metrics", states=["True", "False"], labelnames=['backup_name'])
        self.last_backup =  Gauge("duplicity_last_backup", "Last Backup Date", labelnames=['backup_name'])
        self.elapse_time =  Gauge("duplicity_elapse_time", "Backup Elapse Time", labelnames=['backup_name'])
        self.time_since_backup =  Gauge("duplicity_time_since_backup", "Time Since Last Backup", labelnames=['backup_name'])
        self.errors = Gauge("duplicity_errors", "Backup Errors", labelnames=['backup_name'])
        self.new_files = Gauge("duplicity_new_files", "Number Of New Files", labelnames=['backup_name'])
        self.deleted_files = Gauge("duplicity_deleted_files", "Number Of Deleted Files", labelnames=['backup_name'])
        self.changed_files = Gauge("duplicity_changed_files", "Number Of Changed Files", labelnames=['backup_name'])
        self.delta_entries = Gauge("duplicity_delta_entries", "Delta Of Number Of Files", labelnames=['backup_name'])
        self.raw_delta_size = Gauge("duplicity_raw_delta_size", "Raw Backup Size Delta", labelnames=['backup_name'])
        self.changed_file_size = Gauge("duplicity_changed_file_size", "Sum Size Of Changed Files", labelnames=['backup_name'])
        self.source_file_size = Gauge("duplicity_source_file_size", "", labelnames=['backup_name'])
        self.total_destination_size_change = Gauge("duplicity_total_destination_size_change", "", labelnames=['backup_name'])

        self.pre_backup_date_file_last_backup =  Gauge("duplicity_pre_backup_date_file_date", "Last Pre Backup File Backup Date", labelnames=['backup_name'])
        self.restored_date_file_last_restore_date =  Gauge("duplicity_restored_date_file_last_restore_date", "Last Restore File Date", labelnames=['backup_name'])

    def pre_start_load(self):
        """Pre-Start metric load"""
        with open(self.last_metric_location, encoding="utf-8") as fp:
            self.last_run_metrics = json.load(fp)


    def run_metric_save(self):
        """Save metrics out to disk for container restart"""
         # Update Prometheus metrics with application metrics
        self.got_metrics.labels(container_name=self.backup_name).state(str(self.last_run_metrics["getSuccess"]))
        if self.last_run_metrics["getSuccess"]:
            self.last_backup.labels(container_name=self.backup_name).set(self.last_run_metrics["lastBackup"])
            self.time_since_backup.labels(container_name=self.backup_name).set(self.last_run_metrics["timeSinceBackup"])
            self.errors.labels(container_name=self.backup_name).set(self.last_run_metrics["errors"])
            self.new_files.labels(container_name=self.backup_name).set(self.last_run_metrics["files"]["new"])
            self.deleted_files.labels(container_name=self.backup_name).set(self.last_run_metrics["files"]["deleted"])
            self.changed_files.labels(container_name=self.backup_name).set(self.last_run_metrics["files"]["changed"])
            self.delta_entries.labels(container_name=self.backup_name).set(self.last_run_metrics["files"]["delta"])
            self.raw_delta_size.labels(container_name=self.backup_name).set(self.last_run_metrics["size"]["rawDelta"])
            self.changed_file_size.labels(container_name=self.backup_name).set(self.last_run_metrics["size"]["changedFiles"])
            self.source_file_size.labels(container_name=self.backup_name).set(self.last_run_metrics["size"]["sourceFile"])
            self.total_destination_size_change.labels(container_name=self.backup_name).set(self.last_run_metrics["size"]["totalDestChange"])

        if self.last_run_metrics["backup-test-file-success"]:
            self.pre_backup_date_file_last_backup.labels(container_name=self.backup_name).set(self.last_run_metrics["backup-test-file-date"])
        if self.last_run_metrics["restore-file-read-success"]:
            self.restored_date_file_last_restore_date.labels(container_name=self.backup_name).set(self.last_run_metrics["restore-file-date"])
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

    backup_name = str(os.getenv("BACKUP_NAME", "duplicy_backup"))
    last_metric_location =  str(os.getenv("LAST_METRIC_LOCATION", "/home/duplicity/config/last_metrics"))
    pre_backup_date_file =  str(os.getenv("DATE_FILE_PRE_BACKUP", "/home/duplicity/backup/test/pre_backup"))
    restored_date_file = str(os.getenv("DATE_FILE_RESTORED", "/home/duplicity/backup/test/restore"))
    backup_interval = int(os.getenv("BACKUP_INTERVAL", ONE_DAY))

    print("Starting Exporter on port: " + str(exporter_port))

    app_metrics = AppMetrics(
        backup_name=backup_name,
        last_metric_location=last_metric_location,
        pre_backup_date_file=pre_backup_date_file,
        restored_date_file=restored_date_file,
        backup_interval=backup_interval
    )

    print("Running pre-run load")
    app_metrics.pre_start_load()

    start_http_server(exporter_port)
    print("Started")
    app_metrics.run_loop()

if __name__ == "__main__":
    main()
