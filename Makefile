TITO_DIR ?= /tmp/tito
PULP_HOST ?= localhost
PULP_USER ?= admin

settings:
	@echo "PULP_HOST = $(PULP_HOST)"
	@echo "TEST_ARGS = $(TEST_ARGS)"
	@echo "TITO_ARGS = $(TITO_ARGS)"
	@echo "TITO_DIR = $(TITO_DIR)"

rpmclean:
	rm -rf $(TITO_DIR)

rpmcheck:
	tito build --rpm --test $(TITO_ARGS)

rpmtag:
	tito tag $(TITO_ARGS)

pushtag:
	git push && git push --tags

rpm:
	tito build --rpm $(TITO_ARGS)

pulp-auth:
	pulp-admin --host $(PULP_HOST) auth login --username=$(PULP_USER) --password=$(PULP_PASS)

devinstall:
	python httpd-dev.py --install

devuninstall:
	python httpd-dev.py --uninstall

test:
	./run_tests.sh $(TEST_ARGS)
