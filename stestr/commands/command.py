class Command(object):
    """A command that can be run.

    Commands contain non-UI non-domain specific behaviour - they are the
    glue between the UI and the object model.

    Commands are parameterised with:
    :ivar ui: a UI object which is responsible for brokering the command
        arguments, input and output. There is no default ui, it must be
        passed to the constructor.
    
    :ivar repository_factory: a repository factory which is used to create or
        open repositories. The default repository factory is suitable for
        use in the command line tool.

    Commands declare that they accept/need/emit:
    :ivar args: A list of stestr.arguments.AbstractArgument instances.
        AbstractArgument arguments are validated when set_command is called on
        the UI layer.
    :ivar input_streams: A list of stream specifications. Mandatory streams
        are specified by a simple name. Optional streams are specified by
        a simple name with a ? ending the name. Optional multiple streams are
        specified by a simple name with a * ending the name, and mandatory
        multiple streams by ending the name with +. Multiple streams are used
        when a command can process more than one stream.
    :ivar options: A list of optparse.Option options to accept. These are
        merged with global options by the UI layer when set_command is called.
    """

    # class defaults to no streams.
    input_streams = []
    # class defaults to no arguments.
    args = []
    # class defaults to no options.
    options = []

    def __init__(self, ui):
        """Create a Command object with ui ui."""
        self.ui = ui
        self.repository_factory = file.RepositoryFactory()
        self._init()

    def execute(self):
        """Execute a command.

        This interrogates the UI to ensure that arguments and options are
        supplied, performs any validation for the same that the command needs
        and finally calls run() to perform the command. Most commands should
        not need to override this method, and any user wanting to run a 
        command should call this method.

        This is a synchronous method, and basically just a helper. GUI's or
        asynchronous programs can choose to not call it and instead should call
        lower level API's.
        """
        if not self.ui.set_command(self):
            return 1
        try:
            result = self.run()
        except Exception:
            error_tuple = sys.exc_info()
            self.ui.output_error(error_tuple)
            return 3
        if not result:
            return 0
        return result

    @classmethod
    def get_summary(klass):
        docs = klass.__doc__.split('\n')
        return docs[0]

    def _init(self):
        """Per command init call, called into by Command.__init__."""

    def run(self):
        """The core logic for this command to be implemented by subclasses."""
        raise NotImplementedError(self.run)
