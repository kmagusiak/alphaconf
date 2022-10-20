import invoke
from omegaconf import OmegaConf

from . import run as _application_run
from .internal import Application, arg_parser

__doc__ = """Invoke wrapper for an application

Adding the following lines at the end of the file adds support for alphaconf
to inject the configuration.

    ns = Collection(...)
    alphaconf.invoke.run(__name__, ns)
"""


class InvokeAction(arg_parser.Action):
    def handle(self, result, value):
        result.rest.append(value)
        return 'stop'


class InvokeApplication(Application):
    """Application that launched an invoke.Program"""

    def __init__(self, namespace, **properties) -> None:
        super().__init__(**properties)
        self.namespace = namespace
        self.argument_parser.add_argument(
            InvokeAction,
            metavar="-- invoke arguments",
            help="Rest is passed to invoke",
        )

    def _handle_parsed_result(self):
        if self.parsed.result:
            return self.parsed.result.run(self)
        return None

    def run_program(self):
        """Create and run the invoke program"""
        argv = [self.name] + self.parsed.rest
        namespace = self.namespace
        configuration = OmegaConf.to_object(self.configuration)
        namespace.configure(configuration)
        prog = invoke.Program(namespace=namespace, binary=self.name)
        return prog.run(argv)


def run(__name__: str, namespace: invoke.collection.Collection, **properties) -> InvokeApplication:
    """Create an invoke application and run it if __name__ is __main__"""
    app = InvokeApplication(namespace, **properties)
    if __name__ == '__main__':
        # Let's run the application and parse the arguments
        _application_run(app.run_program, app=app)
    else:
        # Just configure the namespace and set the application
        from . import get, set_application

        app.setup_configuration(arguments=False, load_dotenv=False, setup_logging=True)
        set_application(app, merge=True)
        namespace.configure(get(""))
    return app
