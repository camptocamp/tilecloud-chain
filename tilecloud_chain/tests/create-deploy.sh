#! /bin/bash -e

yes ""|adduser --ingroup travis deploy --disabled-password
mkdir /home/deploy/.ssh
ssh-keygen -t rsa -C your_email@youremail.com -P '' -f /home/deploy/.ssh/id_rsa
touch /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
cat /home/travis/.ssh/id_rsa.pub >> /home/deploy/.ssh/authorized_keys
cat /home/deploy/.ssh/id_rsa.pub >> /home/deploy/.ssh/authorized_keys
ln -s /home/deploy/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys2
touch /home/deploy/.ssh/config
echo "Host localhost" >> /home/deploy/.ssh/config
echo "   StrictHostKeyChecking no" >> /home/deploy/.ssh/config
chmod -R g-rw,o-rw /home/deploy/.ssh
chown deploy:travis -R /home/deploy/.ssh
chown deploy /var/cache/deploy/
PY_MAG_VERSION=`python --version 2>&1|sed 's/Python //'|sed 's/.[0-9]$//'`
echo "source ~/virtualenv/python${PY_MAG_VERSION}/bin/activate" >> /home/deploy/.bashrc

#echo "deploy ALL=(postgres) NOPASSWD: ALL" >> /etc/sudoers
echo "deploy ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
echo "travis ALL=(deploy) NOPASSWD: ALL" >> /etc/sudoers
