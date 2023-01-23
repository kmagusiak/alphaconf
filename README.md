# AlphaConf

[![PyPI version](https://badge.fury.io/py/alphaconf.svg)](https://pypi.org/project/alphaconf/)

A small library to ease writing parameterized scripts.
The goal is to execute a single script and be able to overwrite the parameters
easily.
The configuration is based on [OmegaConf](https://omegaconf.readthedocs.io/).
Optionally, loading from toml is possible.

To run multiple related tasks, there is an integration with
[invoke](https://www.pyinvoke.org).
If you need something more complex, like running multiple instances of the
script, take a look at [hydra-core](https://hydra.cc) or use another script
to launch multiple instances.

## Demo and application

To run an application, you need...

```python
# myapp.py
import alphaconf
import logging
# define the default values and helpers
alphaconf.setup_configuration("""
server:
    url: http://default
""", {
    "server.url": "The URL to show here",
})

def main():
    log = logging.getLogger()
    log.info('server.url:', alphaconf.get('server.url'))
    log.info('has server.user:', alphaconf.get('server.user', bool))

if __name__ == '__main__':
    alphaconf.run(main)
```

Invoking:
```bash
python myapp.py server.url=http://github.com
```

During an interactive session, you can set the application in the current
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
- PYTHON_ALPHACONF may contain a path to a configuration file
- configuration files from configuration directories (using application name)
- environment variables based on key prefixes,
  except "BASE" and "PYTHON";
  if you have a configuration key "abc", all environment variables starting
  with "ABC_" will be loaded where keys are converted to lower case and "_"
  to ".": "ABC_HELLO=a" would set "abc.hello=a"
- key-values from the program arguments

Finally, the configuration is fully resolved and logging is configured.

## Configuration templates and resolvers

Omegaconf's resolvers may be used as configuration values.
For example, `${oc.env:USER,me}` would resolve to the environment variable
USER with a default value "me".
Similarly, `${oc.select:path}` will resolve to another configuration value.

Additional resolvers are added to read file contents.
These are the same as type casts: read_text, read_strip, read_bytes.

The select is used to build multiple templates for configurations by providing
base configurations.
An argument `--select key=template` is a shortcut for
`key=${oc.select:base.key.template}`.
So, `logging: ${oc.select:base.logging.default}` resolves to the configuration
dict defined in base.logging.default and you can select it using
`--select logging=default`.

## Configuration values and integrations

### Typed-configuration

You can use *omegaconf* with *dataclasses* to specify which values are
enforced in the configuration.
Alternatively, the *get* method can receive a data type or a function
which will parse the value.
By default, bool, str, Path, DateTime, etc. are supported.

### Secrets

When showing the configuration, by default configuration keys which are
secrets, keys or passwords will be masked.
Another good practice is to have a file containing the password which
you can retrieve using `alphaconf.get('secret_file', 'read_strip')`.

### Invoke integration

Just add the lines below to parameterize invoke.
Note that the argument parsing to overwrite configuration will work only
when the script is directly called.

```python
import alphaconf.invoke
ns = alphaconf.invoke.collection(globals())
alphaconf.setup_configuration({'backup': 'all'})
alphaconf.invoke.run(__name__, ns)
```

### Interactive and manual usage

Use `alphaconf.interactive.mount()` or load manually create an
`alphaconf.Application`, configure it and set it.
