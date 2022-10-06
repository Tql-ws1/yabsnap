set -uexo pipefail

readonly MY_PATH=$(cd $(dirname "$0") && pwd)

cd $MY_PATH

rsync -aAXHSv src/ /usr/share/yabsnap --delete
ln -sf /usr/share/yabsnap/yabsnap.sh /usr/bin/yabsnap

cp artifacts/yabsnap.service /etc/systemd/system
cp artifacts/yabsnap.timer /etc/systemd/system
systemctl daemon-reload
systemctl enable yabsnap.timer --now
