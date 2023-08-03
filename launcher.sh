cd /home/pi/Projects/targetsys
which python
activate() {
. bin/activate
}
activate
which python
bin/gunicorn  app:app

