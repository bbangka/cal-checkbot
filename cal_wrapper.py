"""
Cal.com API wrapper for LangChain tools.

This module provides a modular interface to Cal.com API v2 with comprehensive
timezone handling, booking management, and error handling capabilities.
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import pytz
import requests
from datetime import datetime, timezone
from langchain_core.tools import tool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging - set to DEBUG level to see detailed timezone conversion logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BookingStatus(Enum):
    """Enum for booking status values."""
    ACCEPTED = "accepted"
    PENDING = "pending"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class FormatType(Enum):
    """Enum for datetime format types."""
    TIME_ONLY = "time_only"
    DATE_TIME = "date_time"
    FRIENDLY = "friendly"
    DEFAULT = "datetime"


@dataclass
class ApiResponse:
    """Structured response from API calls."""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


class TimezoneHandler:
    """Handles all timezone conversion operations with robust error handling."""

    @staticmethod
    def convert_utc_to_user_timezone(
        utc_datetime_str: str,
        user_timezone: str = "UTC"
    ) -> datetime:
        """
        Convert UTC datetime string to user's timezone.

        Args:
            utc_datetime_str: UTC datetime string from API
            user_timezone: Target timezone (e.g., 'America/New_York')

        Returns:
            datetime: Converted datetime object

        Raises:
            ValueError: If timezone conversion fails
        """
        try:
            utc_dt = datetime.fromisoformat(
                utc_datetime_str.replace("Z", "+00:00"))

            if user_timezone == "UTC":
                return utc_dt

            user_tz = pytz.timezone(user_timezone)
            return utc_dt.astimezone(user_tz)
        except (pytz.UnknownTimeZoneError, ValueError) as e:
            logger.warning(f"Timezone conversion error: {e}")
            # Return current UTC datetime as fallback
            return datetime.now(pytz.UTC)

    @staticmethod
    def convert_user_time_to_utc(
        date_str: str,
        time_str: str,
        user_timezone: str = "UTC"
    ) -> datetime:
        """
        Convert user's local date/time to UTC for API comparison.

        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HH:MM format
            user_timezone: User's timezone

        Returns:
            datetime: UTC datetime object
        """
        try:
            target_datetime_str = f"{date_str} {time_str}"
            target_dt = datetime.strptime(
                target_datetime_str, '%Y-%m-%d %H:%M')

            if user_timezone == "UTC":
                return target_dt.replace(tzinfo=pytz.UTC)

            user_tz = pytz.timezone(user_timezone)
            target_dt_with_tz = user_tz.localize(target_dt)
            return target_dt_with_tz.astimezone(pytz.UTC)
        except (pytz.UnknownTimeZoneError, ValueError) as e:
            logger.warning(f"User time to UTC conversion error: {e}")
            # Fallback: return current UTC time
            return datetime.now(pytz.UTC)

    @staticmethod
    def convert_iso_to_utc_api_format(
        start_time_iso: str,
        user_timezone: str = "UTC"
    ) -> str:
        """
        Convert ISO datetime string to UTC format required by Cal.com v2 API.

        Args:
            start_time_iso: ISO 8601 datetime string
            user_timezone: User's timezone

        Returns:
            str: UTC formatted string for API

        Raises:
            ValueError: If datetime format is invalid
        """
        try:
            dt_object = datetime.fromisoformat(
                start_time_iso.replace("Z", "+00:00"))
            if dt_object.tzinfo is None:
                user_tz = pytz.timezone(user_timezone)
                dt_object = user_tz.localize(dt_object)

            utc_time = dt_object.astimezone(pytz.UTC).strftime(
                '%Y-%m-%dT%H:%M:%S.%fZ'
            )[:-3] + 'Z'
            return utc_time
        except (ValueError, pytz.UnknownTimeZoneError) as e:
            logger.error(
                f"Error parsing start_time_iso '{start_time_iso}': {e}")
            raise ValueError(
                f"Invalid start time format '{start_time_iso}'. "
                "Please use ISO 8601 format."
            ) from e

    @staticmethod
    def parse_utc_datetime_string(utc_datetime_str: str) -> datetime:
        """
        Parse UTC datetime string from Cal.com API.

        Args:
            utc_datetime_str: UTC datetime string from API

        Returns:
            datetime: Parsed datetime object

        Raises:
            ValueError: If datetime format is invalid
        """
        try:
            return datetime.fromisoformat(utc_datetime_str.replace("Z", "+00:00"))
        except ValueError as e:
            logger.error(
                f"Error parsing UTC datetime '{utc_datetime_str}': {e}")
            raise ValueError(
                f"Invalid UTC datetime format: {utc_datetime_str}") from e


class DateTimeFormatter:
    """Handles datetime formatting for display with multiple format options."""

    FORMAT_PATTERNS = {
        FormatType.TIME_ONLY: '%H:%M',
        FormatType.DATE_TIME: '%Y-%m-%d %H:%M',
        FormatType.FRIENDLY: '%B %d, %Y at %I:%M %p',
        FormatType.DEFAULT: '%Y-%m-%d %H:%M'
    }

    @classmethod
    def format_for_display(
        cls,
        dt: datetime,
        user_timezone: str = "UTC",
        format_type: Union[str, FormatType] = FormatType.DEFAULT
    ) -> str:
        """
        Format datetime for user display.

        Args:
            dt: Datetime object to format
            user_timezone: User's timezone (for reference)
            format_type: Type of formatting to apply

        Returns:
            str: Formatted datetime string
        """
        try:
            # Convert string to enum if needed
            if isinstance(format_type, str):
                format_type = FormatType(format_type)

            pattern = cls.FORMAT_PATTERNS.get(
                format_type, cls.FORMAT_PATTERNS[FormatType.DEFAULT])
            return dt.strftime(pattern)
        except (ValueError, KeyError) as e:
            logger.warning(f"DateTime formatting error: {e}")
            return str(dt)


class CalApiConfig:
    """
    Handles Cal.com API configuration and setup with validation.

    Attributes:
        api_key: Cal.com API key from environment
        base_url: Base URL for Cal.com API v2
        event_type_id: Event type ID for bookings
        user_email: Default user email
    """

    # Constants
    DEFAULT_BASE_URL = "https://api.cal.com/v2"
    DEFAULT_API_VERSION = "2024-08-13"
    SLOTS_API_VERSION = "2024-09-04"

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.api_key = os.getenv("CAL_API_KEY")
        self.base_url = os.getenv("CAL_BASE_URL", self.DEFAULT_BASE_URL)
        self.event_type_id = os.getenv("CAL_EVENT_TYPE_ID")
        self.user_email = os.getenv("USER_EMAIL")
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate required configuration and log status."""
        if self.api_key:
            logger.info(f"Using CAL_API_KEY: {self.api_key[:10]}...")
        else:
            logger.warning("CAL_API_KEY is not set!")

        logger.info(f"Using EVENT_TYPE_ID: {self.event_type_id}")
        logger.info(f"Using USER_EMAIL: {self.user_email}")

        if not self.api_key:
            raise ValueError("CAL_API_KEY environment variable is required")

    def get_headers(self, api_version: Optional[str] = None) -> Dict[str, str]:
        """
        Get headers for Cal.com API requests.

        Args:
            api_version: API version to use (defaults to DEFAULT_API_VERSION)

        Returns:
            Dict[str, str]: Headers for API requests
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "cal-api-version": api_version or self.DEFAULT_API_VERSION
        }

    @property
    def is_configured(self) -> bool:
        """Check if essential configuration is present."""
        return bool(self.api_key) and bool(self.event_type_id)


class CalApiClient:
    """
    Handles all Cal.com API interactions with comprehensive error handling.

    This class provides a clean interface to the Cal.com API v2 with proper
    error handling, logging, and response formatting.
    """

    def __init__(self, config: CalApiConfig):
        """
        Initialize API client with configuration.

        Args:
            config: CalApiConfig instance with API credentials
        """
        self.config = config
        self.timezone_handler = TimezoneHandler()
        self.formatter = DateTimeFormatter()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        api_version: Optional[str] = None,
        **kwargs
    ) -> ApiResponse:
        """
        Make HTTP request to Cal.com API with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            api_version: API version to use
            **kwargs: Additional arguments for requests

        Returns:
            ApiResponse: Structured response object
        """
        url = f"{self.config.base_url}/{endpoint.lstrip('/')}"
        headers = self.config.get_headers(api_version)

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            logger.debug(f"{method} {url} - Status: {response.status_code}")

            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return ApiResponse(
                    success=False,
                    error=error_msg,
                    status_code=response.status_code
                )

            return ApiResponse(
                success=True,
                data=response.json(),
                status_code=response.status_code
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return ApiResponse(success=False, error=str(e))
        except ValueError as e:
            logger.error(f"JSON parsing failed: {e}")
            return ApiResponse(success=False, error=f"Invalid JSON response: {e}")

    def get_bookings(self, user_email: str) -> ApiResponse:
        """
        Fetch bookings for a user.

        Args:
            user_email: Email address of the user

        Returns:
            ApiResponse: API response with booking data
        """
        return self._make_request(
            "GET",
            "bookings",
            params={"attendeeEmail": user_email}
        )

    def get_available_slots(
        self,
        date: str,
        event_type_id: str,
        user_timezone: str
    ) -> ApiResponse:
        """
        Fetch available slots for a date.

        Args:
            date: Date in YYYY-MM-DD format
            event_type_id: Event type ID
            user_timezone: User's timezone

        Returns:
            ApiResponse: API response with slot data
        """
        start_time = f"{date}T00:00:00Z"
        end_time = f"{date}T23:59:59Z"

        return self._make_request(
            "GET",
            "slots",
            api_version=CalApiConfig.SLOTS_API_VERSION,
            params={
                "eventTypeId": event_type_id,
                "start": start_time,
                "end": end_time,
                "format": "range",
                "timeZone": user_timezone
            }
        )

    def create_booking(self, payload: Dict) -> ApiResponse:
        """
        Create a new booking.

        Args:
            payload: Booking data payload

        Returns:
            ApiResponse: API response with booking creation result
        """
        return self._make_request("POST", "bookings", json=payload)

    def cancel_booking(
        self,
        booking_uid: str,
        reason: str = "User requested cancellation"
    ) -> ApiResponse:
        """
        Cancel a booking.

        Args:
            booking_uid: Unique identifier for the booking
            reason: Cancellation reason

        Returns:
            ApiResponse: API response with cancellation result
        """
        return self._make_request(
            "POST",
            f"bookings/{booking_uid}/cancel",
            json={"cancellationReason": reason}
        )

    def reschedule_booking(self, booking_uid: str, payload: Dict) -> ApiResponse:
        """
        Reschedule a booking.

        Args:
            booking_uid: Unique identifier for the booking
            payload: Reschedule data payload

        Returns:
            ApiResponse: API response with reschedule result
        """
        return self._make_request(
            "POST",
            f"bookings/{booking_uid}/reschedule",
            json=payload
        )


class BookingMatcher:
    """Handles finding bookings based on user criteria with improved error handling."""

    def __init__(self, timezone_handler: TimezoneHandler, formatter: DateTimeFormatter):
        """
        Initialize booking matcher.

        Args:
            timezone_handler: Instance for timezone conversions
            formatter: Instance for datetime formatting
        """
        self.timezone_handler = timezone_handler
        self.formatter = formatter

    def find_booking_by_time(
        self,
        bookings: List[Dict],
        target_date: str,
        target_time: str,
        user_timezone: str
    ) -> Optional[Dict]:
        """
        Find a booking that matches the specified date and time.

        Args:
            bookings: List of booking dictionaries
            target_date: Target date in YYYY-MM-DD format
            target_time: Target time in HH:MM format
            user_timezone: User's timezone

        Returns:
            Optional[Dict]: Matching booking or None
        """
        try:
            target_dt_utc = self.timezone_handler.convert_user_time_to_utc(
                target_date, target_time, user_timezone
            )

            for booking in bookings:
                if booking.get('status', '').lower() != BookingStatus.ACCEPTED.value:
                    continue

                booking_start = booking.get('start', '')
                if not booking_start:
                    continue

                try:
                    booking_dt_utc = self.timezone_handler.parse_utc_datetime_string(
                        booking_start
                    )

                    # Compare datetime objects directly (truncate seconds and microseconds)
                    booking_time_truncated = booking_dt_utc.replace(
                        second=0, microsecond=0)
                    target_time_truncated = target_dt_utc.replace(
                        second=0, microsecond=0)

                    if booking_time_truncated == target_time_truncated:
                        return booking
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Error parsing booking time {booking_start}: {e}")
                    continue

            return None
        except Exception as e:
            logger.error(f"Error in find_booking_by_time: {e}")
            return None

    def format_booking_list(
        self,
        bookings: List[Dict],
        user_timezone: str,
        limit: int = 5
    ) -> List[str]:
        """
        Format bookings for display.

        Args:
            bookings: List of booking dictionaries
            user_timezone: User's timezone for display
            limit: Maximum number of bookings to format

        Returns:
            List[str]: Formatted booking strings
        """
        formatted_bookings = []

        for booking in bookings[:limit]:
            try:
                title = booking.get('title', 'Untitled')
                start = booking.get('start', '')

                if not start:
                    formatted_bookings.append(
                        f"- {title}: No start time available")
                    continue

                booking_dt_user_tz = self.timezone_handler.convert_utc_to_user_timezone(
                    start, user_timezone
                )
                display_time = self.formatter.format_for_display(
                    booking_dt_user_tz, user_timezone, FormatType.DATE_TIME
                )
                formatted_bookings.append(
                    f"- {title}: {display_time} ({user_timezone})"
                )
            except Exception as e:
                logger.warning(f"Error formatting booking: {e}")
                formatted_bookings.append(
                    f"- {booking.get('title', 'Unknown')}: {booking.get('start', 'Unknown time')}"
                )

        return formatted_bookings


# Helper function to reduce code duplication
def _get_upcoming_accepted_bookings(user_email: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    Fetches and filters bookings to return only upcoming accepted bookings.

    Args:
        user_email: Email address of the user

    Returns:
        Tuple[Optional[List[Dict]], Optional[str]]: (accepted_bookings, error_message)
        Returns (bookings_list, None) on success or (None, error_string) on failure
    """
    # Fetch bookings using the API client
    response = api_client.get_bookings(user_email)

    if not response.success:
        return None, f"Error fetching bookings: {response.error}"

    if not response.data or response.data.get("status") != "success":
        error_msg = response.data.get(
            'error', 'Unknown error') if response.data else 'No data'
        return None, f"Error: API returned failure. Details: {error_msg}"

    # Filter accepted bookings and exclude past meetings
    all_bookings = response.data.get("data", [])
    current_time_utc = datetime.now(pytz.UTC)

    accepted_bookings = []
    for booking in all_bookings:
        # Check if booking is accepted
        if booking.get('status', '').lower() != BookingStatus.ACCEPTED.value:
            continue

        # Check if booking is in the future
        booking_start = booking.get('start', '')
        if booking_start:
            try:
                booking_dt_utc = timezone_handler.parse_utc_datetime_string(
                    booking_start)
                # Only include bookings that start in the future
                if booking_dt_utc > current_time_utc:
                    accepted_bookings.append(booking)
            except Exception as e:
                logger.warning(
                    f"Error parsing booking start time {booking_start}: {e}")
                # Include booking if we can't parse the time (to be safe)
                accepted_bookings.append(booking)

    return accepted_bookings, None


# Initialize global instances - following dependency injection pattern
try:
    config = CalApiConfig()
    api_client = CalApiClient(config)
    timezone_handler = TimezoneHandler()
    formatter = DateTimeFormatter()
    booking_matcher = BookingMatcher(timezone_handler, formatter)
except Exception as e:
    logger.error(f"Failed to initialize Cal.com API components: {e}")
    raise


@tool
def list_bookings(user_email: str, user_timezone: str = "UTC") -> str:
    """
    Retrieves a list of accepted bookings for the specified user email.

    Args:
        user_email: Email address of the user
        user_timezone: Timezone for display (e.g., 'America/New_York')

    Returns:
        str: Formatted list of accepted bookings
    """
    logger.info(
        f"Fetching accepted bookings for {user_email} in {user_timezone}")

    # Use helper function to get upcoming accepted bookings
    accepted_bookings, error_msg = _get_upcoming_accepted_bookings(user_email)

    if error_msg:
        return error_msg

    if not accepted_bookings:
        return "No upcoming accepted bookings found for that email."

    # Format bookings for display
    formatted_bookings = []
    for booking in accepted_bookings:
        title = booking.get('title', 'Untitled')
        start = booking.get('start', '')
        end = booking.get('end', '')
        uid = booking.get('uid', 'No UID')

        try:
            start_dt_user_tz = timezone_handler.convert_utc_to_user_timezone(
                start, user_timezone
            )
            end_dt_user_tz = timezone_handler.convert_utc_to_user_timezone(
                end, user_timezone
            )

            start_formatted = formatter.format_for_display(
                start_dt_user_tz, user_timezone, FormatType.DATE_TIME
            )
            end_formatted = formatter.format_for_display(
                end_dt_user_tz, user_timezone, FormatType.TIME_ONLY
            )

            formatted_bookings.append(
                f"- Title: {title}, Start: {start_formatted}, End: {end_formatted} "
                f"({user_timezone}), Booking UID: {uid}"
            )
        except Exception as e:
            logger.warning(f"Error formatting booking {uid}: {e}")
            formatted_bookings.append(
                f"- Title: {title}, Start: {start}, End: {end}, Booking UID: {uid}"
            )

    return (
        f"Upcoming accepted bookings ({len(accepted_bookings)} found) in {user_timezone}:\n"
        + "\n".join(formatted_bookings)
    )


@tool
def get_available_slots(date: str, user_timezone: str = "UTC") -> str:
    """
    Gets available time slots for a specific date.

    Args:
        date: Date in YYYY-MM-DD format
        user_timezone: Timezone (e.g., 'America/New_York', 'Europe/London')

    Returns:
        str: Formatted list of available slots
    """
    logger.info(f"Fetching available slots for {date} in {user_timezone}")

    if not config.event_type_id:
        return "Error: EVENT_TYPE_ID is not configured. Please check your .env file."

    # Fetch slots using the API client
    response = api_client.get_available_slots(
        date, config.event_type_id, user_timezone)

    if not response.success:
        return f"Error fetching available slots: {response.error}"

    if not response.data or response.data.get("status") != "success":
        error_msg = response.data.get(
            'error', 'Unknown error') if response.data else 'No data'
        return f"Error: API returned failure. Details: {error_msg}"

    slots_data = response.data.get("data", {})

    if not slots_data or date not in slots_data:
        return f"No available slots found for {date}."

    slots = slots_data[date]
    if not slots:
        return f"No available slots found for {date}."

    # Format slots for display
    formatted_slots = []
    for i, slot in enumerate(slots, 1):
        start = slot.get("start", "")
        end = slot.get("end", "")

        try:
            start_dt_user_tz = timezone_handler.convert_utc_to_user_timezone(
                start, user_timezone
            )
            end_dt_user_tz = timezone_handler.convert_utc_to_user_timezone(
                end, user_timezone
            )

            start_time = formatter.format_for_display(
                start_dt_user_tz, user_timezone, FormatType.TIME_ONLY
            )
            end_time = formatter.format_for_display(
                end_dt_user_tz, user_timezone, FormatType.TIME_ONLY
            )

            formatted_slots.append(
                f"{i}. {start_time} - {end_time} {user_timezone}")
        except Exception as e:
            logger.warning(f"Error formatting slot {i}: {e}")
            formatted_slots.append(f"{i}. {start} - {end}")

    return f"Available slots for {date} ({user_timezone}):\n" + "\n".join(formatted_slots)


@tool
def create_booking(
    start_time_iso: str,
    user_name: str,
    user_email: str,
    title: str,
    user_timezone: str = "UTC"
) -> str:
    """
    Books a new event on the calendar.

    Args:
        start_time_iso: Start time in ISO 8601 format
        user_name: Name of the attendee
        user_email: Email of the attendee
        title: Meeting title
        user_timezone: User's timezone

    Returns:
        str: Booking confirmation message
    """
    logger.info(
        f"Attempting to book meeting for {user_email} at {start_time_iso}")

    if not config.event_type_id:
        return "Error: EVENT_TYPE_ID is not configured. Please check your .env file."

    # Convert time to UTC format for API
    try:
        utc_time = timezone_handler.convert_iso_to_utc_api_format(
            start_time_iso, user_timezone
        )
    except ValueError as e:
        return str(e)

    # Prepare booking payload
    payload = {
        "start": utc_time,
        "attendee": {
            "name": user_name,
            "email": user_email,
            "timeZone": user_timezone
        },
        "eventTypeId": int(config.event_type_id)
    }

    logger.debug(f"Sending booking payload: {payload}")

    # Create booking using API client
    response = api_client.create_booking(payload)

    if not response.success:
        return f"Error: Booking creation failed. {response.error}"

    if not response.data or response.data.get("status") != "success":
        error_msg = response.data.get(
            'error', 'Unknown error') if response.data else 'No data'
        return f"Error: Booking creation failed. API response: {error_msg}"

    booking_data = response.data.get("data", {})
    booking_uid = booking_data.get("uid", "Unknown UID")

    # Format confirmation message
    try:
        dt_user_tz = timezone_handler.convert_utc_to_user_timezone(
            start_time_iso, user_timezone
        )
        display_time = formatter.format_for_display(
            dt_user_tz, user_timezone, FormatType.FRIENDLY
        )

        return (
            f"Success! Meeting '{title}' booked for {user_name} on {display_time} "
            f"({user_timezone}). Confirmation sent to {user_email}. "
            f"Booking UID: {booking_uid}"
        )
    except Exception as e:
        logger.warning(f"Error formatting confirmation message: {e}")
        return (
            f"Success! Meeting '{title}' booked for {user_name} at {start_time_iso}. "
            f"Confirmation sent to {user_email}. Booking UID: {booking_uid}"
        )


@tool
def cancel_booking(user_email: str, date: str, time: str, user_timezone: str = "UTC") -> str:
    """
    Cancels a booking for the specified user based on date and time.

    Args:
        user_email: Email address of the user
        date: Date in YYYY-MM-DD format
        time: Time in HH:MM format (24-hour)
        user_timezone: Timezone (e.g., 'America/New_York')

    Returns:
        str: Cancellation confirmation message
    """
    logger.info(
        f"Attempting to cancel booking for {user_email} on {date} at {time}")

    # Use helper function to get upcoming accepted bookings
    accepted_bookings, error_msg = _get_upcoming_accepted_bookings(user_email)

    if error_msg:
        return f"Error: Could not retrieve bookings. {error_msg}"

    if not accepted_bookings:
        return "No upcoming accepted bookings found for that email."

    # Find matching booking
    matching_booking = booking_matcher.find_booking_by_time(
        accepted_bookings, date, time, user_timezone
    )

    if not matching_booking:
        # Show available bookings to help user
        booking_list = booking_matcher.format_booking_list(
            accepted_bookings, user_timezone, 5
        )
        available_list = "\n".join(
            booking_list) if booking_list else "None found"
        return (
            f"No booking found for {date} at {time} ({user_timezone}). "
            f"Your upcoming accepted bookings:\n{available_list}"
        )

    # Cancel the found booking
    booking_uid = matching_booking.get('uid')
    booking_title = matching_booking.get('title', 'Untitled')

    if not booking_uid:
        return "Error: Booking UID not found in booking data."

    cancel_response = api_client.cancel_booking(
        booking_uid, "User requested cancellation via chatbot"
    )

    if not cancel_response.success:
        return f"Error: Could not cancel the booking. {cancel_response.error}"

    if not cancel_response.data or cancel_response.data.get("status") != "success":
        error_msg = cancel_response.data.get(
            'error', 'Unknown error') if cancel_response.data else 'No data'
        return f"Error: Could not cancel the booking. API response: {error_msg}"

    try:
        booking_dt_user_tz = timezone_handler.convert_utc_to_user_timezone(
            matching_booking['start'], user_timezone
        )
        display_time = formatter.format_for_display(
            booking_dt_user_tz, user_timezone, FormatType.FRIENDLY
        )

        return (
            f"Success! Booking '{booking_title}' scheduled for {display_time} "
            f"({user_timezone}) has been cancelled. Booking UID: {booking_uid}"
        )
    except Exception as e:
        logger.warning(f"Error formatting cancellation message: {e}")
        return f"Success! Booking '{booking_title}' has been cancelled. Booking UID: {booking_uid}"


@tool
def reschedule_booking(
    user_email: str,
    current_date: str,
    current_time: str,
    new_start_time_iso: str,
    user_timezone: str = "UTC"
) -> str:
    """
    Reschedules an existing booking to a new time.

    Args:
        user_email: Email address of the user
        current_date: Current date in YYYY-MM-DD format
        current_time: Current time in HH:MM format
        new_start_time_iso: New time in ISO 8601 format
        user_timezone: User's timezone

    Returns:
        str: Reschedule confirmation message
    """
    logger.info(
        f"Attempting to reschedule booking for {user_email} from {current_date} "
        f"{current_time} to {new_start_time_iso}"
    )

    # Debug logging for input parameters
    logger.debug(f"RESCHEDULE INPUT - User Email: {user_email}")
    logger.debug(f"RESCHEDULE INPUT - Current Date: {current_date}")
    logger.debug(f"RESCHEDULE INPUT - Current Time: {current_time}")
    logger.debug(
        f"RESCHEDULE INPUT - New Start Time ISO: {new_start_time_iso}")
    logger.debug(f"RESCHEDULE INPUT - User Timezone: {user_timezone}")

    # Use helper function to get upcoming accepted bookings
    accepted_bookings, error_msg = _get_upcoming_accepted_bookings(user_email)

    if error_msg:
        return f"Error: Could not retrieve bookings. {error_msg}"

    if not accepted_bookings:
        return "No upcoming accepted bookings found for that email."

    # Debug logging for timezone conversion of current time
    try:
        current_dt_utc = timezone_handler.convert_user_time_to_utc(
            current_date, current_time, user_timezone
        )
        logger.debug(
            f"RESCHEDULE CONVERSION - Current time in user timezone: {current_date} {current_time} ({user_timezone})")
        logger.debug(
            f"RESCHEDULE CONVERSION - Current time converted to UTC: {current_dt_utc}")
        logger.debug(
            f"RESCHEDULE CONVERSION - Current time UTC formatted for comparison: {formatter.format_for_display(current_dt_utc, 'UTC', FormatType.DATE_TIME)}")
    except Exception as e:
        logger.error(
            f"RESCHEDULE ERROR - Failed to convert current time to UTC: {e}")
        return f"Error: Invalid current date/time format. {e}"

    # Find the booking to reschedule
    matching_booking = booking_matcher.find_booking_by_time(
        accepted_bookings, current_date, current_time, user_timezone
    )

    if not matching_booking:
        # Debug logging for available bookings
        logger.debug(
            f"RESCHEDULE DEBUG - No matching booking found for {current_date} {current_time}")
        logger.debug(f"RESCHEDULE DEBUG - Available accepted bookings:")
        for i, booking in enumerate(accepted_bookings[:5]):
            booking_start = booking.get('start', 'No start time')
            try:
                booking_dt_utc = timezone_handler.parse_utc_datetime_string(
                    booking_start)
                booking_formatted = formatter.format_for_display(
                    booking_dt_utc, "UTC", FormatType.DATE_TIME)
                logger.debug(
                    f"  {i+1}. {booking.get('title', 'No title')}: {booking_start} (UTC: {booking_formatted})")
            except Exception as e:
                logger.debug(
                    f"  {i+1}. {booking.get('title', 'No title')}: {booking_start} (parsing error: {e})")

        # Show available bookings to help user
        booking_list = booking_matcher.format_booking_list(
            accepted_bookings, user_timezone, 5
        )
        available_list = "\n".join(
            booking_list) if booking_list else "None found"
        return (
            f"No booking found for {current_date} at {current_time} ({user_timezone}). "
            f"Your upcoming accepted bookings:\n{available_list}"
        )

    # Debug logging for new time conversion
    try:
        new_utc_time = timezone_handler.convert_iso_to_utc_api_format(
            new_start_time_iso, user_timezone
        )
        logger.debug(
            f"RESCHEDULE CONVERSION - New time ISO input: {new_start_time_iso}")
        logger.debug(
            f"RESCHEDULE CONVERSION - New time converted to UTC API format: {new_utc_time}")

        # Also log the parsed new time for comparison
        new_dt_parsed = timezone_handler.parse_utc_datetime_string(
            new_utc_time)
        logger.debug(
            f"RESCHEDULE CONVERSION - New time parsed back: {new_dt_parsed}")
        logger.debug(
            f"RESCHEDULE CONVERSION - New time in user timezone: {timezone_handler.convert_utc_to_user_timezone(new_utc_time, user_timezone)}")
    except ValueError as e:
        logger.error(f"RESCHEDULE ERROR - Failed to convert new time: {e}")
        return str(e)

    # Get the booking details
    booking_uid = matching_booking.get('uid')
    booking_title = matching_booking.get('title', 'Untitled')

    if not booking_uid:
        return "Error: Booking UID not found in booking data."

    logger.debug(
        f"RESCHEDULE MATCH - Found booking to reschedule: {booking_title} (UID: {booking_uid})")
    logger.debug(
        f"RESCHEDULE MATCH - Original booking start time: {matching_booking.get('start', 'Unknown')}")

    # Reschedule the booking using Cal.com API v2 reschedule endpoint
    reschedule_payload = {
        "start": new_utc_time,
        "rescheduledBy": user_email,
        "reschedulingReason": "User requested reschedule via chatbot"
    }

    logger.debug(f"RESCHEDULE PAYLOAD - Sending to API: {reschedule_payload}")

    reschedule_response = api_client.reschedule_booking(
        booking_uid, reschedule_payload)

    if not reschedule_response.success:
        return f"Error: Could not reschedule the booking. {reschedule_response.error}"

    if not reschedule_response.data or reschedule_response.data.get("status") != "success":
        error_msg = reschedule_response.data.get(
            'error', 'Unknown error') if reschedule_response.data else 'No data'
        return f"Error: Reschedule failed. API response: {error_msg}"

    try:
        # Convert both old and new times to user's timezone for display
        old_booking_dt_user_tz = timezone_handler.convert_utc_to_user_timezone(
            matching_booking['start'], user_timezone
        )
        old_display_time = formatter.format_for_display(
            old_booking_dt_user_tz, user_timezone, FormatType.FRIENDLY
        )

        new_booking_dt_user_tz = timezone_handler.convert_utc_to_user_timezone(
            new_start_time_iso, user_timezone
        )
        new_display_time = formatter.format_for_display(
            new_booking_dt_user_tz, user_timezone, FormatType.FRIENDLY
        )

        return (
            f"✅ Successfully rescheduled '{booking_title}'!\n"
            f"From: {old_display_time} ({user_timezone})\n"
            f"To: {new_display_time} ({user_timezone})\n"
            f"Booking UID: {booking_uid}"
        )
    except Exception as e:
        logger.warning(f"Error formatting reschedule message: {e}")
        return f"✅ Successfully rescheduled '{booking_title}'! Booking UID: {booking_uid}"
