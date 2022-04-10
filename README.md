# Alphaconf

[![PyPI version](https://badge.fury.io/py/alphaconf.svg)](https://pypi.org/project/alphaconf/)

A small library to ease writing parameterized scripts.
The goal is to execute a single script and be able to overwrite the parameters
easily.
The configuration is based on [omegaconf](https://omegaconf.readthedocs.io/).

To run multiple related tasks, there is an integration with
[invoke](https://www.pyinvoke.org).
If you need something more complex, like running multiple instances of the
script, take a look at [hydra-core](https://hydra.cc) or use another script
to launch multiple instances.

## Demo and application

[DEMO](./demo.ipynb)

To run an application, you need...

    import alphaconf
    # each module or application can declare the default configuration they need
    # it will always be loaded before application startup
    alphaconf.setup_configuration("""
    server:
      url: http://default
      user: ${oc.env:USER}
    """)

    def main():
        log = logging.getLogger()
        # get the DictConfig from the current application
        log.info('app name:', alphaconf.configuration().application.name)
        # shortcut to get an option as a dict, str, etc.
        log.info('server.user:', alphaconf.get('server.user'))
        log.info('has server.user:', alphaconf.get('server.user', bool))

    if __name__ == '__main__':
        # run the application
        alphaconf.Application(
            name='example',
            version='0.1',
        ).run(main)

## Secrets

When showing the configuration, by default configuration keys which are
secrets, keys or passwords will be masked.
Another good practice is to have a file containing the password which
you can retrieve using `alphaconf.get('secret_file', 'read_strip')`.

## Invoke integration

Just add the lines below to parameterize invoke.
Note that the argument parsing to overwrite configuration will work only
when the script is directly called.

    ns = Collection()  # define the invoke configuration
    import alphaconf.invoke
    alphaconf.setup_configuration({'backup': 'all'})
    alphaconf.invoke.invoke_application(__name__, ns)


## How the configuration is loaded

When running a program, first dotenv is used to load environment variables
from a `.env` file - this is optional.

Then configuration is built from:

- default configurations defined using (`alphaconf.setup_configuration`)
- `application` key is generated
- configuration files from the system (from your HOME and configuration
  directories)
- environment variables based on key prefixes,
  except "BASE" and "PYTHON";
  if you have a configuration key "abc", all environment variables starting
  with "ABC_" will be loaded where keys are converted to lower case and "_"
  to ".": "ABC_HELLO=a" would set "abc.hello=a"
- key-values from the program arguments

Finally, the configuration is fully resolved once and logging is configured.

## Configuration templates and resolvers

Omegaconf's resolvers may be used as configuration values.
For example, `${oc.env:USER,me}` would resolve to the environment variable
USER with a default value "me".
Similarly, `${oc.select:path}` will resolve to another configuration value.

The select is used to build multiple templates for configurations by providing
base configurations.
An argument `--select key=template` is a shortcut for
`key=${oc.select:base.key.template}`.
So, `logging: ${oc.select:base.logging.default}` resolves to the configuration
dict defined in base.logging.default and you can select it using
`--select logging=default`.
