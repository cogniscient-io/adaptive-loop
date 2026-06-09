class AdaptiveLoopError(Exception):
    pass


class ParseError(AdaptiveLoopError):
    pass


class AdapterError(AdaptiveLoopError):
    pass


class TemplateError(AdaptiveLoopError):
    pass
