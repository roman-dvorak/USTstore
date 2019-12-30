import os
import sys

from plugins.helpers.exceptions import AssertionHTTPError


def _get_frame_filename_function_line(frame_number):
    """ frame_number je relativní vůči kódu, který volá tuto fci """
    last_frame = sys._getframe(frame_number + 1)  # jeden frame je toto
    last_frame_code = last_frame.f_code

    filename = os.path.basename(last_frame_code.co_filename)
    name = last_frame_code.co_name
    line = last_frame.f_lineno

    return filename, name, line


def assert_equals(first, second):
    if first == second:
        return True
    else:
        filename, name, line = _get_frame_filename_function_line(1)
        raise AssertionHTTPError("values are not equal", filename, name, line)


def assert_true(condition):
    if condition:
        return True
    else:
        filename, name, line = _get_frame_filename_function_line(1)
        raise AssertionHTTPError("condition is not true", filename, name, line)


def assert_isinstance(object_, type_):
    if isinstance(object_, type_):
        return True
    else:
        filename, name, line = _get_frame_filename_function_line(1)
        raise AssertionHTTPError(f"object is '{type(object_)}', not '{type_}'", filename, name, line)
