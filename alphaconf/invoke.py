from typing import Dict, Union

import invoke
from omegaconf import OmegaConf

from .cli import run as _application_run
from .internal import application, arg_parser

__doc__ = """Invoke wrapper for an application

Adding the following lines at the end of the file adds support for alphaconf
to inject the configuration.
Instead of a collection, you could pass `globals()`.

    ns = Collection(...)
    alphaconf.invoke.run(__name__, ns)
"""


class InvokeAction(arg_parser.Action):
    """Apped value to the result and let invoke run (stop parsing)"""

    def handle(self, result, value):
        result.rest.append(value)
        return 'stop'


class InvokeApplication(application.Application):
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
        if self.parsed.rest:
            return None
        return super()._handle_parsed_result()

    def run_program(self):
        """Create and run the invoke program"""
        argv = [self.name, *self.parsed.rest]
        namespace = self.namespace
        configuration = OmegaConf.to_object(self.configuration.c)
        namespace.configure(configuration)
        prog = invoke.Program(namespace=namespace, binary=self.name)
        return prog.run(argv)


def collection(variables: Dict = {}) -> invoke.Collection:
    """Create a new collection base on tasks in the variables"""
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
        import alphaconf
        import alphaconf.logging_util

        alphaconf.set_application(app)
        ns.configure(alphaconf.get(""))
        alphaconf.logging_util.setup_application_logging(
            app.configuration.get('logging', default=None)
        )
    return app
