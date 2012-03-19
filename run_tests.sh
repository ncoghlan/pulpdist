pushd src/
python -m unittest discover -v -t . -s pulpdist/core
python -m unittest discover -v -t . -s pulpdist/pulp_plugins
python -m unittest discover -v -t . -s pulpdist/cli
pulpdist/manage_site.py test $*
popd
