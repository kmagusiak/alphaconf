import invoke

from . import Application, application, arg_parser


class InvokeArgumentParser(arg_parser.ArgumentParser):
    """ArgumentParser for invoke, stops after first unrecognized option"""

    def handle_option(self, arg: str, value: str):
        try:
            return super().handle_option(arg, value)
        except arg_parser.InvalidArgumentError:
            # stop parsing on first unrecognized value
            return 'stop'

    def handle_other_arguments(self):
        return  # do nothing, they will be used by the application


class InvokeApplication(Application):
    """Application that launched an invoke.Program"""

    def __init__(self, **properties) -> None:
        super().__init__(**properties)
        self._arg_parser = InvokeArgumentParser(self._arg_parser.app_properties)
        arg_parser.add_default_option_handlers(self._arg_parser, add_help_version=False)

    def _create_program(self, namespace: invoke.collection.Collection):
        """Create the invoke program"""
        namespace.configure(self.get_config())
        prog = invoke.Program(namespace=namespace, binary=self.name)
        return prog

    def _run_program(self):
        """Run the invoke program"""
        argv = [self.name] + self.argument_parser.other_arguments
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
