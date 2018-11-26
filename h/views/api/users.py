# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from h.auth.util import client_authority
from h.exceptions import PayloadError, ConflictError
from h.presenters import UserJSONPresenter
from h.schemas.api.user import CreateUserAPISchema, UpdateUserAPISchema
from h.schemas import ValidationError
from h.services.user_unique import DuplicateUserError
from h.util.view import json_view


# add by wliang below
import datetime
import pdb 
from pyramid import security
import pyramid_authsanity

from h import i18n
from h.exceptions import APIError
from h.services.user import UserNotActivated
from h.accounts.events import LoginEvent

_ = i18n.TranslationString
import logging
log = logging.getLogger("h")
# add by wliang above


@json_view(route_name='api.users',
           request_method='POST',
           permission='create')
def create(request):
    """
    Create a user.

    This API endpoint allows authorised clients (those able to provide a valid
    Client ID and Client Secret) to create users in their authority. These
    users are created pre-activated, and are unable to log in to the web
    service directly.

    Note: the authority-enforcement logic herein is, by necessity, strange.
    The API accepts an ``authority`` parameter but the only valid value for
    the param is the client's verified authority. If the param does not
    match the client's authority, ``ValidationError`` is raised.

    :raises ValidationError: if ``authority`` param does not match client
                             authority
    :raises ConflictError:   if user already exists
    """

    client_authority_ = client_authority(request)
    schema = CreateUserAPISchema()
    appstruct = schema.validate(_json_payload(request))

    # Enforce authority match
    if appstruct['authority'] != client_authority_:
        raise ValidationError(
            "authority '{auth_param}' does not match client authority".format(
                auth_param=appstruct['authority']
            ))

    user_unique_service = request.find_service(name='user_unique')

    try:
        user_unique_service.ensure_unique(appstruct, authority=client_authority_)
    except DuplicateUserError as err:
        raise ConflictError(err)

    user_signup_service = request.find_service(name='user_signup')
    user = user_signup_service.signup(require_activation=False, **appstruct)
    presenter = UserJSONPresenter(user)
    return presenter.asdict()


@json_view(route_name='api.user',
           request_method='PATCH',
           permission='update')
def update(user, request):
    """
    Update a user.

    This API endpoint allows authorised clients (those able to provide a valid
    Client ID and Client Secret) to update users in their authority.
    """
    schema = UpdateUserAPISchema()
    appstruct = schema.validate(_json_payload(request))

    _update_user(user, appstruct)

    presenter = UserJSONPresenter(user)
    return presenter.asdict()


def _update_user(user, appstruct):
    if 'email' in appstruct:
        user.email = appstruct['email']
    if 'display_name' in appstruct:
        user.display_name = appstruct['display_name']


def _json_payload(request):
    try:
        return request.json_body
    except ValueError:
        raise PayloadError()

# add by wliang 11-22
@json_view(route_name='api.login',
           request_method='POST',
           )
def login(request):
    """
    User Login

    :raises ValidationError: if ``authority`` param does not match client
                             authority
    :raises ConflictError:   if user already exists
    """
    username = request.json_body['username']
    password = request.json_body['password']

    user_service = request.find_service(name='user')
    user_password_service = request.find_service(name='user_password')

    try:
        user = user_service.fetch_for_login(username_or_email=username)
    except UserNotActivated:
        err = _("Please check your email and open the link "
                            "to activate your account.")
        raise APIError(err)

    if user is None or not user_password_service.check_password(user, password):
        err = _('User does not exist.')
        raise APIError(err)


    # copy from AuthController._login
    user.last_login_date = datetime.datetime.utcnow()
    request.registry.notify(LoginEvent(request, user))
 
    ticket_policy = pyramid_authsanity.AuthServicePolicy()
    headers =  ticket_policy.remember(request, user.userid)
    log.info(headers)

    #https://stackoverflow.com/questions/14925652
    request.response.headerlist.extend(headers)
    log.info('-'*100)
    log.info(request.response)

    return { 'successful': True, 'message': 'auth OK'}