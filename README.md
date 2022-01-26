# Alphaconf

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

(DEMO)[demo.ipynb]

To run an application, you need...

    import alphaconf
    # each module or application can declare the default configuration they need
    # it will always be loaded first
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

    if __name__ == '__main__':
        # run the application
        alphaconf.Application(
            name='example',
            version='0.1',
        ).run(main)

## Invoke integration

Just add the lines below to parameterize invoke.
Note that the argument parsing to overwrite configuration will work only
when the script is directly called.

    ns = Collection()  # define the invoke configuration
    import alphaconf.invoke
    alphaconf.setup_configuration({'backup': 'all'})
    alphaconf.invoke.invoke_application(__name__, ns)
