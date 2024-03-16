# Duplicity-With-Prometheus-Metrics
A docker container that runs duplicity on a periodic basis and exposes prometheus metrics

Can be run with the following:
sudo docker run \
-p 9877:9877 \
-e PUID="1001" \
-e PGID="1001" \
-e BACKUP_NAME="duplicity_test" \
-e PASSPHRASE="test" \
-e DUPLICITY_SERVER_SSH_HOST="192.168.1.1" \
-e DUPLICITY_SERVER_REMOTE_PATH="/duplicity_test/kube/test" \
-e DUPLICITY_FULL_IF_OLDER_THAN="1M" \
-e DUPLICITY_SERVER_SSH_KEY_FILE="/home/duplicity/.ssh/id_rsa" \
-e DUPLICITY_SERVER_SSH_KEY_SSH_KEY=$SSH_KEY \
-v /home/tgc/backup_test/config:/home/duplicity/config \
-v /home/tgc/backup_test/data:/backup/data \
-v /home/tgc/backup_test/cache:/home/duplicity/.cache \
-v /home/tgc/backup_test/gnupg:/home/duplicity/.gnupg \
--name duplicity_test \
--rm \
tcousin/duplicty-with-prometheus


The following can be used to restore data:

echo "restore" > /home/<user>/backup_test/data/restore_confirm
sudo docker run \
-p 9877:9877 \
-e PUID="1001" \
-e PGID="1001" \
-e BACKUP_NAME="duplicity_test" \
-e DUPLICITY_RUN_MODE="RESTORE" \
-e PASSPHRASE="test" \
-e DUPLICITY_SERVER_SSH_HOST="192.168.1.1" \
-e DUPLICITY_SERVER_REMOTE_PATH="/duplicity_test/kube/test" \
-e DUPLICITY_FULL_IF_OLDER_THAN="1M" \
-e DUPLICITY_SERVER_SSH_KEY_FILE="/home/duplicity/.ssh/id_rsa" \
-e DUPLICITY_SERVER_SSH_KEY_SSH_KEY=$SSH_KEY \
-v /home/<user>/backup_test/config:/home/duplicity/config \
-v /home/<user>/backup_test/data:/backup/data \
-v /home/<user>/backup_test/cache:/home/duplicity/.cache \
-v /home/<user>/backup_test/gnupg:/home/duplicity/.gnupg \
--name duplicity_test \
--rm \
tcousin/duplicty-with-prometheus
