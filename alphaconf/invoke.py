import invoke

from . import Application, application, arg_parser


class InvokeArgumentParser(arg_parser.ArgumentParser):
    """Argumentparser for invoke"""

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

    def run(self, namespace: invoke.collection.Collection, **configuration):
        # Parse arguments
        def run_program():
            argv = [self.name] + self.argument_parser.other_arguments
            return self._create_program(namespace).run(argv)

        return super().run(run_program, **configuration)


def invoke_application(
    __name__: str, namespace: invoke.collection.Collection, **properties
) -> InvokeApplication:
    """Create an invoke application and run it if __name__ is __main__"""
    app = InvokeApplication(**properties)
    if __name__ == '__main__':
        # Let's run the application and parse the arguments
        app.run(namespace)
    else:
        # Just configure the namespace and set the application
        current_app = application.get()
        if not current_app:
            application.set(app)
        namespace.configure(app.get_config())
    return app
