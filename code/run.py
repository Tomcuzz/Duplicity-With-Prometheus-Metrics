"""Application exporter"""

import os
import time
from prometheus_client import start_http_server, Gauge, Enum
# import requests
# import icloudpd

class AppMetrics:
    """
    Representation of Prometheus metrics and loop to backup and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, backup_name="", pre_backup_date_file="", restored_date_file=""):
        self.backup_name = backup_name
        self.pre_backup_date_file = pre_backup_date_file
        self.restored_date_file = restored_date_file
        print("Adding Metrics")

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

        if self.pre_backup_date_file != "" and self.restored_date_file != "":
            self.pre_backup_date_file_last_backup =  Gauge("duplicity_pre_backup_date_file_date", "Last Pre Backup File Backup Date", labelnames=['backup_name'])
            self.pre_backup_date_file_elapse_Time =  Gauge("duplicity_pre_backup_elapse_time", "Backup Pre Backup File Elapse Time", labelnames=['backup_name'])
            self.restored_date_file_last_restore_date =  Gauge("duplicity_restored_date_file_last_restore_date", "Last Restore File Date", labelnames=['backup_name'])
            self.restored_date_file_last_restore_elapse_Time =  Gauge("duplicity_restored_date_file_last_restore_elapse_time", "Restore File Elapse Time", labelnames=['backup_name'])

    def pre_start_fetch(self):
        """Pre-Start metric fetch"""

    def run_loop(self):
        """Backup fetching loop"""
        while True:
            time.sleep(30)

def main():
    """Main entry point"""

    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))

    backup_name = str(os.getenv("BACKUP_NAME", "backup_name"))
    pre_backup_date_file =  str(os.getenv("DATE_FILE_PRE_BACKUP", ""))
    restored_date_file = str(os.getenv("DATE_FILE_RESTORED", ""))

    print("Starting Exporter on port: " + str(exporter_port))

    app_metrics = AppMetrics(
        backup_name=backup_name,
        pre_backup_date_file=pre_backup_date_file,
        restored_date_file=restored_date_file
    )

    print("Running First Fetch")
    app_metrics.pre_start_fetch()

    start_http_server(exporter_port)
    print("Started")
    app_metrics.run_loop()

if __name__ == "__main__":
    main()