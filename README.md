# AlphaConf

[![PyPI version](https://badge.fury.io/py/alphaconf.svg)](https://pypi.org/project/alphaconf/)

A small library to ease writing parameterized scripts.
The goal is to execute a single script and be able to overwrite the parameters
easily.
The configuration is based on [OmegaConf].
Optionally, loading from toml or using [pydantic] is possible.

## Demo and application

To run an application, you need...

```python
# myapp.py
import alphaconf
import logging
# define the default values and helpers
alphaconf.setup_configuration({
    "server.url": "http://default",
}, {
    "server.url": "The URL to show here",
})

def main():
    log = logging.getLogger()
    log.info('server.url:', alphaconf.get('server.url'))
    log.info('has server.user:', alphaconf.get('server.user', bool, default=False))

if __name__ == '__main__':
    alphaconf.cli.run(main)
```

Invoking:
```bash
python myapp.py server.url=http://github.com
```

During an *interactive session*, you can set the application in the current
context.
```python
# import other modules
import alphaconf.interactive
alphaconf.interactive.mount()
alphaconf.interactive.load_configuration_file('path')
```

Check the [DEMO](./demo.ipynb) for more examples.

## How the configuration is loaded

When running a program, first dotenv is used to load environment variables
from a `.env` file - this is optional.

Then configuration is built from:

- default configurations defined using (`alphaconf.setup_configuration`)
- `application` key is generated
- `PYTHON_ALPHACONF` environment variable may contain a path to load
- configuration files from configuration directories (using application name)
- environment variables based on key prefixes,
  except "BASE" and "PYTHON"; \
  if you have a configuration key "abc", all environment variables starting
  with "ABC_" will be loaded, for example "ABC_HELLO=a" would set "abc.hello=a"
- key-values from the program arguments

Finally, the configuration is fully resolved and logging is configured.

## Configuration templates and resolvers

Configuration values are resolved by [OmegaConf].
Some of the resolvers (standard and custom):
- `${oc.env:USER,me}`: resolve the environment variable USER
  with a default value "me"
- `${oc.select:config_path}`: resolve to another configuration value
- `${read_text:file_path}`: read text contents of a file as `str`
- `${read_bytes:file_path}`: read contents of a file as `bytes`
- `${read_strip:file_path}`: read text contents of a file as strip spaces

The *oc.select* is used to build multiple templates for configurations
by providing base configurations.
An argument `--select key=template` is a shortcut for
`key=${oc.select:base.key.template}`.
So, `logging: ${oc.select:base.logging.default}` resolves to the configuration
dict defined in base.logging.default and you can select it using
`--select logging=default`.

## Configuration values and integrations

### Typed-configuration

You can use [OmegaConf] with [pydantic] to *get* typed values.
```python
class MyConf(pydantic.BaseModel):
    value: int = 0

    def build(self):
        # use as a factory pattern to create more complex objects
        # for example, a connection to the database
        return self.value * 2

# setup the configuration
alphaconf.setup_configuration(MyConf, prefix='a')
# read the value
alphaconf.get('a', MyConf)
v = alphaconf.get(MyConf)  # shortcut, because it's registered as a type
```

### Secrets

When showing the configuration, by default configuration keys which are
secrets, keys or passwords will be masked.
You can read values or passwords from files, by using the template
`${read_strip:/path_to_file}`
or, more securely, read the file in the code
`alphaconf.get('secret_file', Path).read_text().strip()`.

### Inject parameters

We can inject default values to functions from the configuration.
Either one by one, where we can map a factory function or a configuration key.
Or inject all automatically base on the parameter name.

```python
from alphaconf.inject import inject, inject_auto

@inject('name', 'application.name')
@inject_auto(ignore={'name'})
def main(name: str, example=None):
    pass

# similar to
def main(name: str=None, example=None):
    if name is None:
        name = alphaconf.get('application.name', str)
    if example is None:
        example = alphaconf.get('example', default=example)
    ...
```

### Invoke integration

To run multiple related tasks, there is an integration with
[invoke](https://www.pyinvoke.org).
If you need something more complex, like running multiple instances of the
script, take a look at [hydra-core](https://hydra.cc) or use another script
to launch multiple instances.

Just add the lines below to parameterize `invoke`.
Note that the argument parsing to overwrite configuration will work only
when the script is directly called.

```python
import alphaconf.invoke
ns = alphaconf.invoke.collection(globals())
alphaconf.setup_configuration({'backup': 'all'})
alphaconf.invoke.run(__name__, ns)
```

## Plumbum
Replace `invoke` with alphaconf and plumbum.

## Way to 1.0
- Make argument parsing separate from the core
- Compare `plumbum` and `invoke` for building scripts
- Secret handling and encryption
- Run a specific function `alphaconf my.module.main`:
  find functions and inject args
- Install completions for bash `alphaconf --install-autocompletion`

[OmegaConf]: https://omegaconf.readthedocs.io/
[pydantic]: https://docs.pydantic.dev/latest/
