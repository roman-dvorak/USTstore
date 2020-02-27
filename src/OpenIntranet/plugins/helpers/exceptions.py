from tornado.web import HTTPError
from unidecode import unidecode


class BadInputHTTPError(HTTPError):

    def __init__(self, message):
        super().__init__(reason=f"Chybný vstup: {message}")


class MissingInfoHTTPError(HTTPError):

    def __init__(self, message):
        super().__init__(reason=f"Chybí informace: {message}")


class ForbiddenHTTPError(HTTPError):

    def __init__(self, operation=None, details=None):
        operation_str = f" ({operation}) " if operation else " "
        details_str = f": {details}" if details else ""

        reason = f"Pro tuto operaci{operation_str}nemáte dostatečná oprávnění{details_str}"
        # TODO tohle zrušit až se bude vše načítat ajaxem
        reason_ascii = unidecode(reason)

        super().__init__(status_code=403, reason=reason_ascii)
