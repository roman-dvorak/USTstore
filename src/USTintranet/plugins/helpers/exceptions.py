from tornado.web import HTTPError


class BadInputError(HTTPError):

    def __init__(self, message):
        super().__init__(reason=f"Chybný vstup: {message}")


class MissingInfoError(HTTPError):

    def __init__(self, message):
        super().__init__(reason=f"Chybí informace: {message}")
