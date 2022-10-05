import invoke
from omegaconf import OmegaConf

from . import run as _app_run
from .application import Application, arg_parser


class InvokeAction(arg_parser.Action):
    def handle(self, result, value):
        result.rest.append(value)
        return 'stop'


class InvokeApplication(Application):
    """Application that launched an invoke.Program"""

    def __init__(self, **properties) -> None:
        super().__init__(**properties)
        self.namespace = None
        self.argument_parser.add_argument(
            InvokeAction,
            metavar="invoke arguments",
            help="Rest is passed to invoke",
        )

    def _handle_parsed_result(self):
        if self.parsed.result:
            return self.parsed.result.run(self)
        return None

    def _create_program(self, namespace: invoke.collection.Collection):
        """Create the invoke program"""
        configuration = OmegaConf.to_object(self.configuration)
        namespace.configure(configuration)
        prog = invoke.Program(namespace=namespace, binary=self.name)
        return prog

    def _run_program(self):
        """Run the invoke program"""
        argv = [self.name] + self.parsed.rest
        return self._create_program(self.namespace).run(argv)


def run(__name__: str, namespace: invoke.collection.Collection, **properties) -> InvokeApplication:
    """Create an invoke application and run it if __name__ is __main__"""
    app = InvokeApplication(**properties)
    app.namespace = namespace
    if __name__ == '__main__':
        # Let's run the application and parse the arguments
        _app_run(app._run_program, app=app)
    else:
        # Just configure the namespace and set the application
        from . import application

        application.set(app)
        app.setup_configuration(arguments=False, load_dotenv=False, setup_logging=True)
        configuration = OmegaConf.to_object(app.configuration)
        namespace.configure(configuration)
    return app
