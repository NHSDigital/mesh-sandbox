# Contributing

## dependencies
tools used:
- make
- git
- [asdf version manager](https://asdf-vm.com/guide/getting-started.html)


## first run ...  

### install project tools
use asdf to ensure required tools are installed ... configured tools are in  [.tool-versions](.tool-versions)
```bash
cd ~/work/nhs-aws-helpers
asdf plugin add python
asdf plugin add poetry
asdf install
```

### install git hooks
```shell
make refresh-hooks
```

## normal development

### create virtualenv and install python dependencies

```shell
make install
source .venv/bin/activate
```

### start docker containers
```shell
make up
```


### running tests

```shell
make test
```

### testing multiple python versions
to test all python versions configured
```shell
make tox
```


### linting
project uses:
- [ruff](https://docs.astral.sh/ruff/)
- [mypy](https://pypi.org/project/mypy/)

run both with 
```shell
make lint
```
or individually with
```shell
make mypy
```
or
```shell
make ruff 
```


### formatting code
project uses:
- [black](https://pypi.org/project/black/)

lint checks will fail if the code is not formaated correctly

```shell
# make black will run both isort and black
make black
```


