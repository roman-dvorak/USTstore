from tornado.web import HTTPError


class BadInputHTTPError(HTTPError):

    def __init__(self, message):
        super().__init__(reason=f"Chybný vstup: {message}")


class MissingInfoHTTPError(HTTPError):

    def __init__(self, message):
        super().__init__(reason=f"Chybí informace: {message}")


class AssertionHTTPError(HTTPError):

    def __init__(self, message, file_name=None, function_name=None, line_number=None):
        resulting_message = ""
        if file_name:
            resulting_message += f"file: {file_name}, "
        if function_name:
            resulting_message += f"function: {function_name}, "
        if line_number:
            resulting_message += f"line: {line_number}, "

        resulting_message += message

        super().__init__(reason=f"Assertion error: {resulting_message}")
