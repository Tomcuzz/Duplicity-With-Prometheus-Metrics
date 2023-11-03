# Import from a Python image
FROM python:3

#Expose the nessasary volumes
VOLUME ["/saved_data", "/home/duplicity/.cache/duplicity", "/home/duplicity/.gnupg"]

# Create Enviroment Veriables for exporter
ENV EXPORTER_PORT="9877"

# Create Environment veriable for the name of the backup
ENV BACKUP_NAME="duplicy_backup"

# Create Environment veriable for checking backup and restore are working correctly.
ENV DATE_FILE_PRE_BACKUP=""
ENV DATE_FILE_RESTORED=""

# ENV HOME=/home/duplicity

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
 && mkdir -p /home/duplicity/.cache/duplicity \
 && mkdir -p /home/duplicity/.gnupg \
 && chmod -R go+rwx /home/duplicity/

# Brief check duplicity works.
RUN duplicity --version

# Expose port 9877 to the outside world
EXPOSE 9877

# Create health check to check / url
HEALTHCHECK --interval=5m --timeout=3s --start-period=10s --retries=3 CMD curl -f http://localhost:9877/ || exit 1

# Run as duplicity
USER duplicity

# Command to run the executable
CMD [ "python", "-u", "./code/run.py" ]