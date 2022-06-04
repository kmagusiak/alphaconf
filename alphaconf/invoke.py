import invoke

from . import Application, application, arg_parser


class InvokeAction(arg_parser.Action):
    def handle(self, result, value):
        return 'stop'  # TODO add


class InvokeApplication(Application):
    """Application that launched an invoke.Program"""

    def __init__(self, **properties) -> None:
        super().__init__(**properties)
        self.argument_parser.add_argument(InvokeAction)

    def _create_program(self, namespace: invoke.collection.Collection):
        """Create the invoke program"""
        namespace.configure(self.get_config())
        prog = invoke.Program(namespace=namespace, binary=self.name)
        return prog

    def _run_program(self):
        """Run the invoke program"""
        argv = [self.name] + self.parsed.rest
        return self._create_program(self.namespace).run(argv)

    def run_collection(self, namespace: invoke.collection.Collection, **configuration):
        """Set the namespace and run the program

        :param namespace: The invoke collection to run
        :param configuration: Configuration arguments
        """
        self.namespace = namespace
        try:
            return self.run(self._run_program, **configuration)
        finally:
            self.namespace = None


def invoke_application(
    __name__: str, namespace: invoke.collection.Collection, **properties
) -> InvokeApplication:
    """Create an invoke application and run it if __name__ is __main__"""
    app = InvokeApplication(**properties)
    if __name__ == '__main__':
        # Let's run the application and parse the arguments
        app.run_collection(namespace)
    else:
        # Just configure the namespace and set the application
        current_app = application.get(None)
        if not current_app:
            application.set(app)
        namespace.configure(app.get_config())
        app.setup_logging()
    return app
