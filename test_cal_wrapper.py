"""
Simplified test suite for Cal.com API wrapper with fixed type issues.
"""

import pytest
import requests
from unittest.mock import Mock, patch
from datetime import datetime
import pytz

# Import the modules we want to test
from cal_wrapper import (
    TimezoneHandler, DateTimeFormatter, CalApiConfig, CalApiClient,
    BookingMatcher, ApiResponse, BookingStatus, FormatType,
    list_bookings, get_available_slots, create_booking,
    cancel_booking, reschedule_booking
)


class TestTimezoneHandler:
    """Test cases for TimezoneHandler class."""

    def test_convert_utc_to_user_timezone(self):
        """Test UTC to user timezone conversion."""
        utc_time = "2025-07-24T18:00:00.000Z"
        result = TimezoneHandler.convert_utc_to_user_timezone(
            utc_time, "America/New_York")

        assert isinstance(result, datetime)
        # EDT is UTC-4 in July
        assert result.hour == 14

    def test_convert_utc_to_user_timezone_utc(self):
        """Test UTC to UTC conversion (no change)."""
        utc_time = "2025-07-24T18:00:00.000Z"
        result = TimezoneHandler.convert_utc_to_user_timezone(utc_time, "UTC")

        assert isinstance(result, datetime)
        assert result.hour == 18

    def test_convert_utc_to_user_timezone_invalid_timezone(self):
        """Test conversion with invalid timezone."""
        utc_time = "2025-07-24T18:00:00.000Z"
        # Should fall back to UTC time without raising exception
        result = TimezoneHandler.convert_utc_to_user_timezone(
            utc_time, "Invalid/Timezone")

        assert isinstance(result, datetime)

    def test_convert_utc_to_user_timezone_invalid_datetime(self):
        """Test conversion with invalid datetime string."""
        invalid_time = "invalid-datetime"
        # Should fall back gracefully
        result = TimezoneHandler.convert_utc_to_user_timezone(
            invalid_time, "UTC")

        assert isinstance(result, datetime)

    def test_convert_user_time_to_utc(self):
        """Test user timezone to UTC conversion."""
        result = TimezoneHandler.convert_user_time_to_utc(
            "2025-07-24", "14:00", "America/New_York")

        assert isinstance(result, datetime)
        assert result.tzinfo == pytz.UTC

    def test_convert_user_time_to_utc_utc_timezone(self):
        """Test user time to UTC when already in UTC."""
        result = TimezoneHandler.convert_user_time_to_utc(
            "2025-07-24", "14:00", "UTC")

        assert isinstance(result, datetime)
        assert result.tzinfo == pytz.UTC
        assert result.hour == 14

    def test_convert_user_time_to_utc_invalid_timezone(self):
        """Test user time to UTC with invalid timezone."""
        result = TimezoneHandler.convert_user_time_to_utc(
            "2025-07-24", "14:00", "Invalid/Timezone")

        assert isinstance(result, datetime)
        assert result.tzinfo == pytz.UTC

    def test_convert_user_time_to_utc_invalid_time(self):
        """Test user time to UTC with invalid time format."""
        result = TimezoneHandler.convert_user_time_to_utc(
            "invalid-date", "invalid-time", "UTC")

        assert isinstance(result, datetime)
        assert result.tzinfo == pytz.UTC

    def test_convert_iso_to_utc_api_format(self):
        """Test ISO to UTC API format conversion."""
        iso_time = "2025-07-24T14:00:00"
        result = TimezoneHandler.convert_iso_to_utc_api_format(
            iso_time, "America/New_York")

        assert result.endswith('Z')
        assert 'T' in result

    def test_convert_iso_to_utc_api_format_with_z(self):
        """Test ISO to UTC API format with Z suffix."""
        iso_time = "2025-07-24T18:00:00.000Z"
        result = TimezoneHandler.convert_iso_to_utc_api_format(iso_time, "UTC")

        assert result.endswith('Z')
        assert 'T' in result

    def test_convert_iso_to_utc_api_format_invalid(self):
        """Test ISO to UTC API format with invalid input."""
        with pytest.raises(ValueError):
            TimezoneHandler.convert_iso_to_utc_api_format(
                "invalid-date", "UTC")

    def test_parse_utc_datetime_string(self):
        """Test parsing UTC datetime string."""
        utc_time = "2025-07-24T18:00:00.000Z"
        result = TimezoneHandler.parse_utc_datetime_string(utc_time)

        assert isinstance(result, datetime)
        assert result.hour == 18

    def test_parse_utc_datetime_string_invalid(self):
        """Test parsing invalid UTC datetime string."""
        with pytest.raises(ValueError):
            TimezoneHandler.parse_utc_datetime_string("invalid-datetime")


class TestDateTimeFormatter:
    """Test cases for DateTimeFormatter class."""

    def test_format_for_display_time_only(self):
        """Test time-only formatting."""
        dt = datetime(2025, 7, 24, 14, 30)
        result = DateTimeFormatter.format_for_display(
            dt, "UTC", FormatType.TIME_ONLY)

        assert "14:30" in result

    def test_format_for_display_friendly(self):
        """Test friendly formatting."""
        dt = datetime(2025, 7, 24, 14, 30)
        result = DateTimeFormatter.format_for_display(
            dt, "UTC", FormatType.FRIENDLY)

        assert "July" in result
        assert "24" in result

    def test_format_for_display_date_time(self):
        """Test date-time formatting."""
        dt = datetime(2025, 7, 24, 14, 30)
        result = DateTimeFormatter.format_for_display(
            dt, "UTC", FormatType.DATE_TIME)

        assert "2025-07-24 14:30" == result

    def test_format_for_display_default(self):
        """Test default formatting."""
        dt = datetime(2025, 7, 24, 14, 30)
        result = DateTimeFormatter.format_for_display(
            dt, "UTC", FormatType.DEFAULT)

        assert "2025-07-24 14:30" == result

    def test_format_for_display_string_format_type(self):
        """Test formatting with string format type."""
        dt = datetime(2025, 7, 24, 14, 30)
        result = DateTimeFormatter.format_for_display(
            dt, "UTC", "time_only")

        assert "14:30" in result

    def test_format_for_display_invalid_format_type(self):
        """Test formatting with invalid format type."""
        dt = datetime(2025, 7, 24, 14, 30)
        result = DateTimeFormatter.format_for_display(
            dt, "UTC", "invalid_format")

        # Should fall back to string representation
        assert "2025-07-24 14:30:00" in result

    def test_format_for_display_error_handling(self):
        """Test formatting error handling."""
        # Test with a datetime that will cause formatting issues
        with patch.object(DateTimeFormatter, 'FORMAT_PATTERNS', {FormatType.TIME_ONLY: '%invalid_pattern%'}):
            dt = datetime(2025, 7, 24, 14, 30)
            result = DateTimeFormatter.format_for_display(
                dt, "UTC", FormatType.TIME_ONLY)

            # Should fall back to string representation
            assert "2025-07-24 14:30:00" in result


class TestCalApiConfig:
    """Test cases for CalApiConfig class."""

    @patch.dict('os.environ', {
        'CAL_API_KEY': 'test_key',
        'CAL_EVENT_TYPE_ID': '123',
        'CAL_BASE_URL': 'https://test.cal.com'
    })
    def test_config_from_env(self):
        """Test configuration loading from environment."""
        config = CalApiConfig()

        assert config.api_key == "test_key"
        assert config.event_type_id == "123"
        assert config.base_url == "https://test.cal.com"

    @patch.dict('os.environ', {
        'CAL_API_KEY': 'test_key',
        'CAL_EVENT_TYPE_ID': '123'
    }, clear=True)
    def test_config_default_base_url(self):
        """Test default base URL when not specified."""
        config = CalApiConfig()

        assert config.base_url == "https://api.cal.com/v2"

    @patch.dict('os.environ', {}, clear=True)
    def test_config_missing_api_key(self):
        """Test configuration with missing API key."""
        with pytest.raises(ValueError, match="CAL_API_KEY environment variable is required"):
            CalApiConfig()

    @patch.dict('os.environ', {'CAL_API_KEY': 'test_key'})
    def test_get_headers_default_version(self):
        """Test getting headers with default API version."""
        config = CalApiConfig()
        headers = config.get_headers()

        assert headers["Authorization"] == "Bearer test_key"
        assert headers["Content-Type"] == "application/json"
        assert headers["cal-api-version"] == "2024-08-13"

    @patch.dict('os.environ', {'CAL_API_KEY': 'test_key'})
    def test_get_headers_custom_version(self):
        """Test getting headers with custom API version."""
        config = CalApiConfig()
        headers = config.get_headers("2024-09-04")

        assert headers["cal-api-version"] == "2024-09-04"

    @patch.dict('os.environ', {
        'CAL_API_KEY': 'test_key',
        'CAL_EVENT_TYPE_ID': '123'
    })
    def test_is_configured_true(self):
        """Test is_configured property when properly configured."""
        config = CalApiConfig()
        assert config.is_configured is True

    @patch.dict('os.environ', {'CAL_API_KEY': 'test_key'}, clear=True)
    def test_is_configured_false_missing_event_type(self):
        """Test is_configured property when event type ID is missing."""
        config = CalApiConfig()
        assert config.is_configured is False


class TestCalApiClient:
    """Test cases for CalApiClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict('os.environ', {'CAL_API_KEY': 'test_key'}):
            self.config = CalApiConfig()
        self.client = CalApiClient(self.config)

    @patch('cal_wrapper.requests.request')
    def test_get_bookings_success(self, mock_request):
        """Test successful booking retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [{"id": "1", "title": "Test Meeting"}]
        }
        mock_request.return_value = mock_response

        result = self.client.get_bookings("test@example.com")

        assert result.success is True
        assert result.data is not None

    @patch('cal_wrapper.requests.request')
    def test_get_bookings_http_error(self, mock_request):
        """Test booking retrieval with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_request.return_value = mock_response

        result = self.client.get_bookings("test@example.com")

        assert result.success is False
        assert result.error is not None

    @patch('cal_wrapper.requests.request')
    def test_get_available_slots_success(self, mock_request):
        """Test successful slot retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"2025-07-24": [{"start": "09:00", "end": "10:00"}]}
        }
        mock_request.return_value = mock_response

        result = self.client.get_available_slots("2025-07-24", "123", "UTC")

        assert result.success is True
        assert result.data is not None

    @patch('cal_wrapper.requests.request')
    def test_create_booking_success(self, mock_request):
        """Test successful booking creation."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "status": "success",
            "data": {"uid": "booking_123"}
        }
        mock_request.return_value = mock_response

        payload = {"start": "2025-07-24T14:00:00Z",
                   "attendee": {"email": "test@example.com"}}
        result = self.client.create_booking(payload)

        assert result.success is True
        assert result.data is not None

    @patch('cal_wrapper.requests.request')
    def test_cancel_booking_success(self, mock_request):
        """Test successful booking cancellation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_request.return_value = mock_response

        result = self.client.cancel_booking("booking_123")

        assert result.success is True

    @patch('cal_wrapper.requests.request')
    def test_reschedule_booking_success(self, mock_request):
        """Test successful booking reschedule."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_request.return_value = mock_response

        payload = {"start": "2025-07-24T15:00:00Z"}
        result = self.client.reschedule_booking("booking_123", payload)

        assert result.success is True

    @patch('cal_wrapper.requests.request')
    def test_request_exception_handling(self, mock_request):
        """Test handling of request exceptions."""
        mock_request.side_effect = requests.exceptions.RequestException(
            "Network error")

        result = self.client.get_bookings("test@example.com")

        assert result.success is False
        assert result.error is not None
        assert "Network error" in result.error

    @patch('cal_wrapper.requests.request')
    def test_json_parsing_error(self, mock_request):
        """Test handling of JSON parsing errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_request.return_value = mock_response

        result = self.client.get_bookings("test@example.com")

        assert result.success is False
        assert result.error is not None
        assert "Invalid JSON" in result.error

    @patch('cal_wrapper.requests.request')
    def test_make_request_with_custom_api_version(self, mock_request):
        """Test making request with custom API version."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_request.return_value = mock_response

        result = self.client._make_request(
            "GET", "test", api_version="2024-09-04")

        assert result.success is True
        # Verify the API version was passed in headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        headers = call_args[1]['headers']
        assert headers['cal-api-version'] == "2024-09-04"


class TestBookingMatcher:
    """Test cases for BookingMatcher class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.timezone_handler = TimezoneHandler()
        self.formatter = DateTimeFormatter()
        self.matcher = BookingMatcher(self.timezone_handler, self.formatter)

    def test_find_booking_by_time_found(self):
        """Test finding a booking by time."""
        bookings = [
            {
                "uid": "123",
                "title": "Test Meeting",
                "start": "2025-07-24T18:00:00.000Z",
                "status": "accepted"
            }
        ]

        result = self.matcher.find_booking_by_time(
            bookings, "2025-07-24", "14:00", "America/New_York"
        )

        assert result is not None
        assert result["uid"] == "123"


class TestLangChainTools:
    """Test cases for LangChain tool functions."""

    @patch('cal_wrapper.api_client')
    def test_list_bookings(self, mock_api_client):
        """Test the list_bookings tool function."""
        # Create a future datetime for testing
        from datetime import datetime, timedelta
        import pytz
        future_time = (datetime.now(pytz.UTC) + timedelta(days=1)
                       ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        mock_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": [
                    {
                        "status": "accepted",
                        "title": "Test Meeting",
                        "uid": "123",
                        "start": future_time,
                        "end": future_time
                    }
                ]
            }
        )
        mock_api_client.get_bookings.return_value = mock_response

        # Call the tool using invoke
        result = list_bookings.invoke(
            {"user_email": "test@example.com", "user_timezone": "UTC"})

        assert "Test Meeting" in result
        assert "123" in result

    @patch('cal_wrapper.api_client')
    def test_list_bookings_error(self, mock_api_client):
        """Test list_bookings with API error."""
        mock_response = ApiResponse(
            success=False,
            error="API Error"
        )
        mock_api_client.get_bookings.return_value = mock_response

        result = list_bookings.invoke(
            {"user_email": "test@example.com", "user_timezone": "UTC"})

        assert "Error fetching bookings" in result

    @patch('cal_wrapper.api_client')
    def test_list_bookings_filters_past_meetings(self, mock_api_client):
        """Test that list_bookings filters out past meetings."""
        from datetime import datetime, timedelta
        import pytz

        # Create past and future times
        past_time = (datetime.now(pytz.UTC) - timedelta(days=1)
                     ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'
        future_time = (datetime.now(pytz.UTC) + timedelta(days=1)
                       ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        mock_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": [
                    {
                        "status": "accepted",
                        "title": "Past Meeting",
                        "uid": "past123",
                        "start": past_time,
                        "end": past_time
                    },
                    {
                        "status": "accepted",
                        "title": "Future Meeting",
                        "uid": "future123",
                        "start": future_time,
                        "end": future_time
                    }
                ]
            }
        )
        mock_api_client.get_bookings.return_value = mock_response

        result = list_bookings.invoke(
            {"user_email": "test@example.com", "user_timezone": "UTC"})

        # Should only include future meeting
        assert "Future Meeting" in result
        assert "future123" in result
        assert "Past Meeting" not in result
        assert "past123" not in result
        assert "Upcoming accepted bookings (1 found)" in result


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_api_response_dataclass(self):
        """Test ApiResponse dataclass functionality."""
        response = ApiResponse(success=True, data={"test": "data"})
        assert response.success is True
        assert response.data is not None
        assert response.error is None

    def test_booking_status_enum(self):
        """Test BookingStatus enum values."""
        assert BookingStatus.ACCEPTED.value == "accepted"
        assert BookingStatus.PENDING.value == "pending"
        assert BookingStatus.CANCELLED.value == "cancelled"

    def test_format_type_enum(self):
        """Test FormatType enum values."""
        assert FormatType.TIME_ONLY.value == "time_only"
        assert FormatType.FRIENDLY.value == "friendly"
