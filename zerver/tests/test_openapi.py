# -*- coding: utf-8 -*-

import re
import sys
import mock
import inspect
import typing
from typing import Dict, Any, Set, Union, List, Callable, Tuple, Optional, Iterable

from django.conf import settings
from django.http import HttpResponse

import zerver.lib.openapi as openapi
from zerver.lib.request import REQ
from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.openapi import (
    get_openapi_fixture, get_openapi_parameters,
    validate_against_openapi_schema, to_python_type,
    SchemaError, openapi_spec, get_openapi_paths
)
from zerver.lib.request import arguments_map

TEST_ENDPOINT = '/messages/{message_id}'
TEST_METHOD = 'patch'
TEST_RESPONSE_BAD_REQ = '400'
TEST_RESPONSE_SUCCESS = '200'

VARMAP = {
    'integer': int,
    'string': str,
    'boolean': bool,
    'array': list,
    'Typing.List': list,
    'NoneType': None,
}

class OpenAPIToolsTest(ZulipTestCase):
    """Make sure that the tools we use to handle our OpenAPI specification
    (located in zerver/lib/openapi.py) work as expected.

    These tools are mostly dedicated to fetching parts of the -already parsed-
    specification, and comparing them to objects returned by our REST API.
    """
    def test_get_openapi_fixture(self) -> None:
        actual = get_openapi_fixture(TEST_ENDPOINT, TEST_METHOD,
                                     TEST_RESPONSE_BAD_REQ)
        expected = {
            'code': 'BAD_REQUEST',
            'msg': 'You don\'t have permission to edit this message',
            'result': 'error'
        }
        self.assertEqual(actual, expected)

    def test_get_openapi_parameters(self) -> None:
        actual = get_openapi_parameters(TEST_ENDPOINT, TEST_METHOD)
        expected_item = {
            'name': 'message_id',
            'in': 'path',
            'description':
                'The ID of the message that you wish to edit/update.',
            'example': 42,
            'required': True,
            'schema': {'type': 'integer'}
        }
        assert(expected_item in actual)

    def test_validate_against_openapi_schema(self) -> None:
        with self.assertRaises(SchemaError,
                               msg=('Extraneous key "foo" in '
                                    'the response\'scontent')):
            bad_content = {
                'msg': '',
                'result': 'success',
                'foo': 'bar'
            }  # type: Dict[str, Any]
            validate_against_openapi_schema(bad_content,
                                            TEST_ENDPOINT,
                                            TEST_METHOD,
                                            TEST_RESPONSE_SUCCESS)

        with self.assertRaises(SchemaError,
                               msg=("Expected type <class 'str'> for key "
                                    "\"msg\", but actually got "
                                    "<class 'int'>")):
            bad_content = {
                'msg': 42,
                'result': 'success',
            }
            validate_against_openapi_schema(bad_content,
                                            TEST_ENDPOINT,
                                            TEST_METHOD,
                                            TEST_RESPONSE_SUCCESS)

        with self.assertRaises(SchemaError,
                               msg='Expected to find the "msg" required key'):
            bad_content = {
                'result': 'success',
            }
            validate_against_openapi_schema(bad_content,
                                            TEST_ENDPOINT,
                                            TEST_METHOD,
                                            TEST_RESPONSE_SUCCESS)

        # No exceptions should be raised here.
        good_content = {
            'msg': '',
            'result': 'success',
        }
        validate_against_openapi_schema(good_content,
                                        TEST_ENDPOINT,
                                        TEST_METHOD,
                                        TEST_RESPONSE_SUCCESS)

        # Overwrite the exception list with a mocked one
        openapi.EXCLUDE_PROPERTIES = {
            TEST_ENDPOINT: {
                TEST_METHOD: {
                    TEST_RESPONSE_SUCCESS: ['foo']
                }
            }
        }
        good_content = {
            'msg': '',
            'result': 'success',
            'foo': 'bar'
        }
        validate_against_openapi_schema(good_content,
                                        TEST_ENDPOINT,
                                        TEST_METHOD,
                                        TEST_RESPONSE_SUCCESS)

    def test_to_python_type(self) -> None:
        TYPES = {
            'string': str,
            'number': float,
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }

        for oa_type, py_type in TYPES.items():
            self.assertEqual(to_python_type(oa_type), py_type)

    def test_live_reload(self) -> None:
        # Force the reload by making the last update date < the file's last
        # modified date
        openapi_spec.last_update = 0
        get_openapi_fixture(TEST_ENDPOINT, TEST_METHOD)

        # Check that the file has been reloaded by verifying that the last
        # update date isn't zero anymore
        self.assertNotEqual(openapi_spec.last_update, 0)

        # Now verify calling it again doesn't call reload
        with mock.patch('zerver.lib.openapi.openapi_spec.reload') as mock_reload:
            get_openapi_fixture(TEST_ENDPOINT, TEST_METHOD)
            self.assertFalse(mock_reload.called)

class OpenAPIArgumentsTest(ZulipTestCase):
    # This will be filled during test_openapi_arguments:
    checked_endpoints = set()  # type: Set[str]
    # TODO: These endpoints need to be documented:
    pending_endpoints = set([
        '/users/me/avatar',
        '/settings/display',
        '/users/me/profile_data',
        '/users/me/pointer',
        '/users/me/presence',
        '/users/me',
        '/bot_storage',
        '/users/me/api_key/regenerate',
        '/default_streams',
        '/default_stream_groups/create',
        '/users/me/alert_words',
        '/users/me/status',
        '/messages/matches_narrow',
        '/settings',
        '/submessage',
        '/attachments',
        '/calls/complete_zoom_user',
        '/calls/register_zoom_user',
        '/export/realm',
        '/zcommand',
        '/realm',
        '/realm/deactivate',
        '/realm/domains',
        '/realm/icon',
        '/realm/logo',
        '/realm/presence',
        '/realm/profile_fields',
        '/queue_id',
        '/invites',
        '/invites/multiuse',
        '/bots',
        # Mobile-app only endpoints
        '/users/me/android_gcm_reg_id',
        '/users/me/apns_device_token',
        # Regex based urls
        '/realm/domains/{domain}',
        '/realm/profile_fields/{field_id}',
        '/users/{user_id}/reactivate',
        '/users/{user_id}',
        '/bots/{bot_id}/api_key/regenerate',
        '/bots/{bot_id}',
        '/invites/{prereg_id}',
        '/invites/{prereg_id}/resend',
        '/invites/multiuse/{invite_id}',
        '/users/me/subscriptions/{stream_id}',
        '/messages/{message_id}/reactions',
        '/messages/{message_id}/emoji_reactions/{emoji_name}',
        '/attachments/{attachment_id}',
        '/user_groups/{user_group_id}/members',
        '/streams/{stream_id}/members',
        '/streams/{stream_id}/delete_topic',
        '/default_stream_groups/{group_id}',
        '/default_stream_groups/{group_id}/streams',
        # Regex with an unnamed capturing group.
        '/users/(?!me/)(?P<email>[^/]*)/presence',
        # Actually '/user_groups/<user_group_id>' in urls.py but fails the reverse mapping
        # test because of the variable name mismatch. So really, it's more of a buggy endpoint.
        '/user_groups/{group_id}',  # Equivalent of what's in urls.py
        '/user_groups/{user_group_id}',  # What's in the OpenAPI docs
    ])
    # TODO: These endpoints have a mismatch between the
    # documentation and the actual API and need to be fixed:
    buggy_documentation_endpoints = set([
        '/events',
        '/users/me/subscriptions/muted_topics',
        # List of flags is broader in actual code; fix is to just add them
        '/settings/notifications',
        # Endpoint is documented; parameters aren't detected properly.
        '/realm/filters',
        '/realm/filters/{filter_id}',
        # Docs need update for subject -> topic migration
        '/messages/{message_id}',
        # stream_id parameter incorrectly appears in both URL and endpoint parameters?
        '/streams/{stream_id}',
        # pattern starts with /api/v1 and thus fails reverse mapping test.
        '/dev_fetch_api_key',
        '/server_settings',
        # Because of the unnamed capturing group, this fails the reverse mapping test.
        '/users/{email}/presence',
    ])

    def convert_regex_to_url_pattern(self, regex_pattern: str) -> str:
        """ Convert regular expressions style URL patterns to their
            corresponding OpenAPI style formats. All patterns are
            expected to start with ^ and end with $.
            Examples:
                1. /messages/{message_id} <-> r'^messages/(?P<message_id>[0-9]+)$'
                2. /events <-> r'^events$'
        """
        self.assertTrue(regex_pattern.startswith("^"))
        self.assertTrue(regex_pattern.endswith("$"))
        url_pattern = '/' + regex_pattern[1:][:-1]
        url_pattern = re.sub(r"\(\?P<(\w+)>[^/]+\)", r"{\1}", url_pattern)
        return url_pattern

    def ensure_no_documentation_if_intentionally_undocumented(self, url_pattern: str,
                                                              method: str,
                                                              msg: Optional[str]=None) -> None:
        try:
            get_openapi_parameters(url_pattern, method)
            if not msg:  # nocoverage
                msg = """
We found some OpenAPI documentation for {method} {url_pattern},
so maybe we shouldn't mark it as intentionally undocumented in the urls.
""".format(method=method, url_pattern=url_pattern)
            raise AssertionError(msg)  # nocoverage
        except KeyError:
            return

    def check_for_non_existant_openapi_endpoints(self) -> None:
        """ Here, we check to see if every endpoint documented in the openapi
        documentation actually exists in urls.py and thus in actual code.
        Note: We define this as a helper called at the end of
        test_openapi_arguments instead of as a separate test to ensure that
        this test is only executed after test_openapi_arguments so that it's
        results can be used here in the set operations. """
        openapi_paths = set(get_openapi_paths())
        undocumented_paths = openapi_paths - self.checked_endpoints
        undocumented_paths -= self.buggy_documentation_endpoints
        undocumented_paths -= self.pending_endpoints
        try:
            self.assertEqual(len(undocumented_paths), 0)
        except AssertionError:  # nocoverage
            msg = "The following endpoints have been documented but can't be found in urls.py:"
            for undocumented_path in undocumented_paths:
                msg += "\n + {}".format(undocumented_path)
            raise AssertionError(msg)

    def get_type_by_priority(self, types: List[type]) -> type:
        priority = {list: 1, str: 2, int: 3, bool: 4}
        tyiroirp = {1: list, 2: str, 3: int, 4: bool}
        val = 5
        for t in types:
            v = priority.get(t, 5)
            if v < val:
                val = v
        return tyiroirp.get(val, types[0])

    def get_standardized_argument_type(self, t: Any) -> type:
        """ Given a type from the typing module such as List[str] or Union[str, int],
        convert it into a corresponding Python type. Unions are mapped to a canonical
        choice among the options.
        E.g. typing.Union[typing.List[typing.Dict[str, typing.Any]], NoneType]
        needs to be mapped to list."""

        if sys.version[:3] == "3.5" and type(t) == typing.UnionMeta:  # nocoverage # in python3.6+
            origin = Union
        else:  # nocoverage  # in python3.5. I.E. this is used in python3.6+
            origin = getattr(t, "__origin__", None)

        if not origin:
            # Then it's most likely one of the fundamental data types
            # I.E. Not one of the data types from the "typing" module.
            return t
        elif origin == Union:
            subtypes = []
            if sys.version[:3] == "3.5":  # nocoverage # in python3.6+
                args = t.__union_params__
            else:  # nocoverage # in python3.5
                args = t.__args__
            for st in args:
                subtypes.append(self. get_standardized_argument_type(st))
            return self.get_type_by_priority(subtypes)
        elif origin == List:
            return list
        elif origin == Iterable:
            return list
        return self. get_standardized_argument_type(t.__args__[0])

    def render_openapi_type_exception(self, function:  Callable[..., HttpResponse],
                                      openapi_params: Set[Tuple[Any, Optional[type]]],
                                      function_params: Set[Tuple[str, type]],
                                      diff: Set[Tuple[Any, Optional[type]]]) -> None:  # nocoverage
        """ Print a *VERY* clear and verbose error message for when the types
        (between the OpenAPI documentation and the function declaration) don't match. """

        msg = """
The types for the request parameters in zerver/openapi/zulip.yaml
do not match the types declared in the implementation of {}.\n""".format(function.__name__)
        msg += '='*65 + '\n'
        msg += "{:<10s}{:^30s}{:>10s}\n".format("Parameter", "OpenAPI Type",
                                                "Function Declaration Type")
        msg += '='*65 + '\n'
        opvtype = None
        fdvtype = None
        for element in diff:
            vname = element[0]
            for element in openapi_params:
                if element[0] == vname:
                    opvtype = element[1]
                    break
            for element in function_params:
                if element[0] == vname:
                    fdvtype = element[1]
                    break
        msg += "{:<10s}{:^30s}{:>10s}\n".format(vname, str(opvtype), str(fdvtype))
        raise AssertionError(msg)

    def check_argument_types(self, function: Callable[..., HttpResponse],
                             openapi_parameters: List[Dict[str, Any]]) -> None:
        """ We construct for both the OpenAPI data and the function's definition a set of
        tuples of the form (var_name, type) and then compare those sets to see if the
        OpenAPI data defines a different type than that actually accepted by the function.
        Otherwise, we print out the exact differences for convenient debugging and raise an
        AssertionError. """
        openapi_params = set([(element["name"], VARMAP[element["schema"]["type"]]) for
                             element in openapi_parameters])

        function_params = set()  # type: Set[Tuple[str, type]]

        # Iterate through the decorators to find the original
        # function, wrapped by has_request_variables, so we can parse
        # its arguments.
        while getattr(function, "__wrapped__", None):
            function = getattr(function, "__wrapped__", None)
            # Tell mypy this is never None.
            assert function is not None

        # Now, we do inference mapping each REQ parameter's
        # declaration details to the Python/mypy types for the
        # arguments passed to it.
        #
        # Because the mypy types are the types used inside the inner
        # function (after the original data is processed by any
        # validators, converters, etc.), they will not always match
        # the API-level argument types.  The main case where this
        # happens is when a `converter` is used that changes the types
        # of its parameters.
        for vname, defval in inspect.signature(function).parameters.items():
            defval = defval.default
            if defval.__class__ == REQ:
                # TODO: The below inference logic in cases where
                # there's a converter function declared is incorrect.
                # Theoretically, we could restructure the converter
                # function model so that we can check what type it
                # excepts to be passed to make validation here
                # possible.

                vtype = self.get_standardized_argument_type(function.__annotations__[vname])
                vname = defval.post_var_name  # type: ignore # See zerver/lib/request.pyi
                function_params.add((vname, vtype))

        diff = openapi_params - function_params
        if diff:  # nocoverage
            self.render_openapi_type_exception(function, openapi_params, function_params, diff)

    def test_openapi_arguments(self) -> None:
        """This end-to-end API documentation test compares the arguments
        defined in the actual code using @has_request_variables and
        REQ(), with the arguments declared in our API documentation
        for every API endpoint in Zulip.

        First, we import the fancy-Django version of zproject/urls.py
        by doing this, each has_request_variables wrapper around each
        imported view function gets called to generate the wrapped
        view function and thus filling the global arguments_map variable.
        Basically, we're exploiting code execution during import.

            Then we need to import some view modules not already imported in
        urls.py. We use this different syntax because of the linters complaining
        of an unused import (which is correct, but we do this for triggering the
        has_request_variables decorator).

            At the end, we perform a reverse mapping test that verifies that
        every url pattern defined in the openapi documentation actually exists
        in code.
        """

        urlconf = __import__(getattr(settings, "ROOT_URLCONF"), {}, {}, [''])

        # We loop through all the API patterns, looking in particular
        # for those using the rest_dispatch decorator; we then parse
        # its mapping of (HTTP_METHOD -> FUNCTION).
        for p in urlconf.v1_api_and_json_patterns:
            if p.lookup_str != 'zerver.lib.rest.rest_dispatch':
                continue

            # since the module was already imported and is now residing in
            # memory, we won't actually face any performance penalties here.
            for method, value in p.default_args.items():
                if isinstance(value, str):
                    function_name = value
                    tags = set()  # type: Set[str]
                else:
                    function_name, tags = value

                lookup_parts = function_name.split('.')
                module = __import__('.'.join(lookup_parts[:-1]), {}, {}, [''])
                function = getattr(module, lookup_parts[-1])

                # Our accounting logic in the `has_request_variables()`
                # code means we have the list of all arguments
                # accepted by every view function in arguments_map.
                accepted_arguments = set(arguments_map[function_name])

                regex_pattern = p.regex.pattern
                url_pattern = self.convert_regex_to_url_pattern(regex_pattern)

                if "intentionally_undocumented" in tags:
                    self.ensure_no_documentation_if_intentionally_undocumented(url_pattern, method)
                    continue

                if url_pattern in self.pending_endpoints:
                    # HACK: After all pending_endpoints have been resolved, we should remove
                    # this segment and the "msg" part of the `ensure_no_...` method.
                    msg = """
We found some OpenAPI documentation for {method} {url_pattern},
so maybe we shouldn't include it in pending_endpoints.
""".format(method=method, url_pattern=url_pattern)
                    self.ensure_no_documentation_if_intentionally_undocumented(url_pattern,
                                                                               method, msg)
                    continue

                try:
                    openapi_parameters = get_openapi_parameters(url_pattern, method)
                except Exception:  # nocoverage
                    raise AssertionError("Could not find OpenAPI docs for %s %s" %
                                         (method, url_pattern))

                # We now have everything we need to understand the
                # function as defined in our urls.py:
                #
                # * method is the HTTP method, e.g. GET, POST, or PATCH
                #
                # * p.regex.pattern is the URL pattern; might require
                #   some processing to match with OpenAPI rules
                #
                # * accepted_arguments is the full set of arguments
                #   this method accepts (from the REQ declarations in
                #   code).
                #
                # * The documented parameters for the endpoint as recorded in our
                #   OpenAPI data in zerver/openapi/zulip.yaml.
                #
                # We now compare these to confirm that the documented
                # argument list matches what actually appears in the
                # codebase.

                openapi_parameter_names = set(
                    [parameter['name'] for parameter in openapi_parameters]
                )

                if len(openapi_parameter_names - accepted_arguments) > 0:
                    print("Undocumented parameters for",
                          url_pattern, method, function_name)
                    print(" +", openapi_parameter_names)
                    print(" -", accepted_arguments)
                    assert(url_pattern in self.buggy_documentation_endpoints)
                elif len(accepted_arguments - openapi_parameter_names) > 0:
                    print("Documented invalid parameters for",
                          url_pattern, method, function_name)
                    print(" -", openapi_parameter_names)
                    print(" +", accepted_arguments)
                    assert(url_pattern in self.buggy_documentation_endpoints)
                else:
                    self.assertEqual(openapi_parameter_names, accepted_arguments)
                    self.check_argument_types(function, openapi_parameters)
                    self.checked_endpoints.add(url_pattern)

        self.check_for_non_existant_openapi_endpoints()
