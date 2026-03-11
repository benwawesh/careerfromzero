"""
Custom exceptions and exception handler for the users app
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Log the exception
        logger.error(
            f"API Error: {exc} | "
            f"View: {context['view'].__class__.__name__} | "
            f"Method: {context['request'].method} | "
            f"Path: {context['request'].path}",
            exc_info=True
        )

        # Format the error response
        custom_response_data = {
            'error': True,
            'message': str(exc),
            'status_code': response.status_code,
        }

        # Add details if available
        if hasattr(response.data, 'items'):
            custom_response_data['details'] = dict(response.data)

        response.data = custom_response_data

    return response


class CustomAPIException(Exception):
    """
    Base class for custom API exceptions
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = 'A server error occurred.'

    def __init__(self, message=None, status_code=None):
        if message is not None:
            self.message = message
        else:
            self.message = self.default_message

        if status_code is not None:
            self.status_code = status_code

        logger.error(f"CustomAPIException: {self.message} (Status: {self.status_code})")
        super().__init__(self.message)


class AuthenticationFailedException(CustomAPIException):
    """Exception raised when authentication fails"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = 'Authentication failed. Please check your credentials.'


class InvalidCredentialsException(CustomAPIException):
    """Exception raised for invalid credentials"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = 'Invalid username or password.'


class UserAlreadyExistsException(CustomAPIException):
    """Exception raised when trying to create a user that already exists"""
    status_code = status.HTTP_409_CONFLICT
    default_message = 'A user with this email already exists.'


class InvalidPasswordException(CustomAPIException):
    """Exception raised for invalid password"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = 'Password does not meet security requirements.'


class UserNotFoundException(CustomAPIException):
    """Exception raised when a user is not found"""
    status_code = status.HTTP_404_NOT_FOUND
    default_message = 'User not found.'


class UnauthorizedAccessException(CustomAPIException):
    """Exception raised when user doesn't have permission"""
    status_code = status.HTTP_403_FORBIDDEN
    default_message = 'You do not have permission to perform this action.'


class ValidationException(CustomAPIException):
    """Exception raised for validation errors"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = 'Validation error occurred.'