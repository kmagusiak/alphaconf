from typing import Dict, Union

import invoke
from omegaconf import OmegaConf

from . import run as _application_run
from .internal import Application, arg_parser

__doc__ = """Invoke wrapper for an application

Adding the following lines at the end of the file adds support for alphaconf
to inject the configuration.
Instead of a collection, you could pass `globals()`.

    ns = Collection(...)
    alphaconf.invoke.run(__name__, ns)
"""


class InvokeAction(arg_parser.Action):
    def handle(self, result, value):
        result.rest.append(value)
        return 'stop'


class InvokeApplication(Application):
    """Application that launched an invoke.Program"""

    def __init__(self, namespace: invoke.Collection, **properties) -> None:
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


def collection(variables: Dict = {}) -> invoke.Collection:
    """Create a new collection"""
    return invoke.Collection(*[v for v in variables.values() if isinstance(v, invoke.Task)])


def run(
    __name__: str, namespace: Union[invoke.collection.Collection, Dict], **properties
) -> InvokeApplication:
    """Create an invoke application and run it if __name__ is __main__"""
    if isinstance(namespace, invoke.Collection):
        ns = namespace
    else:
        ns = collection(namespace)
    app = InvokeApplication(ns, **properties)
    if __name__ == '__main__':
        # Let's run the application and parse the arguments
        _application_run(app.run_program, app=app)
    else:
        # Just configure the namespace and set the application
        from . import get, set_application

        app.setup_configuration(arguments=False, load_dotenv=False, setup_logging=True)
        set_application(app, merge=True)
        ns.configure(get(""))
    return app
