pushd src/
python -m unittest discover -v -t . -s pulpdist/core -s pulpdist/pulp_plugins
pulpdist/manage_site.py test $*
popd
