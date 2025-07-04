# Import from a Python image
FROM python:3

#Expose the nessasary volumes
VOLUME ["/backup/data", "/home/duplicity/config", "/home/duplicity/.cache", "/home/duplicity/.gnupg"]

# Create Enviroment Veriables for exporter
ENV EXPORTER_PORT="9877"

# Create Environment veriable for the name of the backup
ENV BACKUP_NAME="duplicy_backup"

# Create Environment veriable for how often to backup
ENV BACKUP_INTERVAL="86400"

# Create Environment veriable for duplicity passphrase
ENV PASSPHRASE=""

# Create Environment veriable for duplicity configs
ENV DUPLICITY_RUN_MODE="BACKUP"
ENV DUPLICITY_FULL_IF_OLDER_THAN=""
ENV DUPLICITY_REMOVE_ALL_BUT_N_FULL="0"
ENV DUPLICITY_REMOVE_ALL_INC_OF_BUT_N_FULL="0"
ENV RESTORE_TO_TIME=""
ENV DUPLICITY_VERBOSITY=""
ENV DUPLICITY_ALLOW_SOURCE_MISMATCH = "True"

# Create Environment veriable for storage locations.
ENV LAST_METRIC_LOCATION="/home/duplicity/config/last_metrics"
ENV DATE_FILE_RESTORED="/home/duplicity/config/restore_test.txt"
ENV DUPLICITY_SERVER_REMOTE_PATH="/home/duplicity/backup"
ENV DATE_FILE_PRE_BACKUP="test/pre_backup.txt"

# Duplicity backup server location.
ENV DUPLICITY_SERVER_CONNECTION_TYPE="ssh"
ENV DUPLICITY_SERVER_SSH_HOST="192.168.1.1"
ENV DUPLICITY_SERVER_SSH_PORT="22"
ENV DUPLICITY_SERVER_SSH_USER="duplicity"
ENV DUPLICITY_SERVER_SSH_KEY_SSH_KEY=""
ENV DUPLICITY_SERVER_SSH_KEY_FILE="/home/duplicity/config/id_rsa"
ENV DUPLICITY_SERVER_SSH_STRICT_HOST_KEY_CHECKING="False"

# Setup the working directory
WORKDIR /usr/src/app

#Copy the code into the conatiner
COPY . .

# Update apt-get
RUN apt-get update

# Install duplicity
RUN apt-get install duplicity -y

#Install the Python dependancies
RUN pip install --no-cache-dir -r requirements.txt

RUN set -x \
    # Run as non-root user.
 && adduser --disabled-password --uid 1896 duplicity \
 && mkdir -p /home/duplicity/config \
 && mkdir -p /home/duplicity/.cache/duplicity \
 && mkdir -p /home/duplicity/.gnupg \
 && mkdir -p /backup \
 && mkdir -p /backup/data \
 && mkdir -p /backup/test \
 && chmod -R go+rwx /home/duplicity/ \
 && chown -R duplicity:duplicity /home/duplicity/ \
 && chmod -R 700 /home/duplicity/.gnupg \
 && chown -R duplicity:duplicity /backup/ \
 && chmod -R go+rwx /backup/

# Brief check duplicity works.
RUN duplicity --version

# Expose port 9877 to the outside world
EXPOSE 9877

# Create health check to check / url
HEALTHCHECK --interval=5m --timeout=3s --start-period=10s --retries=3 CMD curl -f http://localhost:9877/ || exit 1

# Run as duplicity
# USER duplicity

# Command to run the executable
CMD [ "python", "-u", "./code/run.py" ]
