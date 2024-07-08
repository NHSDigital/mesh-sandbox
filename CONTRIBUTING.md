# Contributing

## Dependencies
Tools used:
- make
- git
- [asdf version manager](https://asdf-vm.com/guide/getting-started.html)


## First run ...  

### Install project tools
Use asdf to ensure required tools are installed ... configured tools are in  [.tool-versions](.tool-versions)
```bash
cd ~/work/nhs-aws-helpers
asdf plugin add python
asdf plugin add poetry
asdf install
```

### Install git hooks
```shell
make refresh-hooks
```

## Normal development

### Create virtualenv and install python dependencies

```shell
make install
source .venv/bin/activate
```

### Start docker containers
```shell
make up
```


### Running tests

```shell
make test
```

### Testing multiple python versions
To test all python versions configured
```shell
make tox
```


### Linting
Project uses:
- [ruff](https://docs.astral.sh/ruff/)
- [mypy](https://pypi.org/project/mypy/)

Run both with 
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


### Formatting code
Project uses:
- [black](https://pypi.org/project/black/)

Lint checks will fail if the code is not formaated correctly

```shell
# make black will run both isort and black
make black
```


