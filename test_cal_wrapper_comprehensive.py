"""
Comprehensive test suite for Cal.com API wrapper to achieve high code coverage.
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
import os

# Import the modules we want to test
from cal_wrapper import (
    TimezoneHandler, DateTimeFormatter, CalApiConfig, CalApiClient,
    BookingMatcher, ApiResponse, BookingStatus, FormatType,
    list_bookings, get_available_slots, create_booking,
    cancel_booking, reschedule_booking
)


class TestBookingMatcherComprehensive:
    """Comprehensive test cases for BookingMatcher class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.timezone_handler = TimezoneHandler()
        self.formatter = DateTimeFormatter()
        self.matcher = BookingMatcher(self.timezone_handler, self.formatter)

    def test_find_booking_by_time_no_accepted_booking(self):
        """Test finding booking when none are accepted."""
        bookings = [
            {
                "uid": "123",
                "title": "Test Meeting",
                "start": "2025-07-24T18:00:00.000Z",
                "status": "pending"  # Not accepted
            }
        ]

        result = self.matcher.find_booking_by_time(
            bookings, "2025-07-24", "14:00", "America/New_York"
        )

        assert result is None

    def test_find_booking_by_time_no_start_time(self):
        """Test finding booking when booking has no start time."""
        bookings = [
            {
                "uid": "123",
                "title": "Test Meeting",
                "start": "",  # Empty start time
                "status": "accepted"
            }
        ]

        result = self.matcher.find_booking_by_time(
            bookings, "2025-07-24", "14:00", "America/New_York"
        )

        assert result is None

    def test_find_booking_by_time_invalid_booking_start(self):
        """Test finding booking with invalid start time format."""
        bookings = [
            {
                "uid": "123",
                "title": "Test Meeting",
                "start": "invalid-datetime",
                "status": "accepted"
            }
        ]

        result = self.matcher.find_booking_by_time(
            bookings, "2025-07-24", "14:00", "America/New_York"
        )

        assert result is None

    def test_find_booking_by_time_exception_handling(self):
        """Test exception handling in find_booking_by_time."""
        with patch.object(self.timezone_handler, 'convert_user_time_to_utc', side_effect=Exception("Test error")):
            bookings = [{"uid": "123", "status": "accepted",
                         "start": "2025-07-24T18:00:00.000Z"}]

            result = self.matcher.find_booking_by_time(
                bookings, "2025-07-24", "14:00", "America/New_York"
            )

            assert result is None

    def test_format_booking_list_no_start_time(self):
        """Test formatting booking list when booking has no start time."""
        bookings = [
            {
                "title": "Test Meeting",
                "start": ""  # Empty start time
            }
        ]

        result = self.matcher.format_booking_list(bookings, "UTC", 5)

        assert len(result) == 1
        assert "No start time available" in result[0]

    def test_format_booking_list_formatting_error(self):
        """Test formatting booking list with error in timezone conversion."""
        bookings = [
            {
                "title": "Test Meeting",
                "start": "2025-07-24T18:00:00.000Z"
            }
        ]

        with patch.object(self.timezone_handler, 'convert_utc_to_user_timezone', side_effect=Exception("Test error")):
            result = self.matcher.format_booking_list(bookings, "UTC", 5)

            assert len(result) == 1
            assert "Test Meeting" in result[0]
            assert "2025-07-24T18:00:00.000Z" in result[0]

    def test_format_booking_list_with_limit(self):
        """Test formatting booking list respects limit."""
        bookings = [
            {"title": f"Meeting {i}", "start": "2025-07-24T18:00:00.000Z"}
            for i in range(10)
        ]

        result = self.matcher.format_booking_list(bookings, "UTC", 3)

        assert len(result) == 3
        assert "Meeting 0" in result[0]
        assert "Meeting 2" in result[2]


class TestLangChainToolsComprehensive:
    """Comprehensive test cases for LangChain tool functions."""

    @patch('cal_wrapper.api_client')
    def test_list_bookings_no_data(self, mock_api_client):
        """Test list_bookings when API returns no data."""
        mock_response = ApiResponse(
            success=True,
            data=None
        )
        mock_api_client.get_bookings.return_value = mock_response

        result = list_bookings.invoke(
            {"user_email": "test@example.com", "user_timezone": "UTC"})

        assert "Error: API returned failure" in result

    @patch('cal_wrapper.api_client')
    def test_list_bookings_api_failure_status(self, mock_api_client):
        """Test list_bookings when API returns failure status."""
        mock_response = ApiResponse(
            success=True,
            data={
                "status": "failure",
                "error": "API Error Message"
            }
        )
        mock_api_client.get_bookings.return_value = mock_response

        result = list_bookings.invoke(
            {"user_email": "test@example.com", "user_timezone": "UTC"})

        assert "Error: API returned failure" in result
        assert "API Error Message" in result

    @patch('cal_wrapper.api_client')
    def test_list_bookings_parsing_error(self, mock_api_client):
        """Test list_bookings with booking time parsing error."""
        # Create a past and future booking, with one having invalid start time
        future_time = (datetime.now(pytz.UTC) + timedelta(days=1)
                       ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        mock_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": [
                    {
                        "status": "accepted",
                        "title": "Valid Meeting",
                        "uid": "valid123",
                        "start": future_time,
                        "end": future_time
                    },
                    {
                        "status": "accepted",
                        "title": "Invalid Meeting",
                        "uid": "invalid123",
                        "start": "invalid-datetime",  # Invalid datetime
                        "end": future_time
                    }
                ]
            }
        )
        mock_api_client.get_bookings.return_value = mock_response

        result = list_bookings.invoke(
            {"user_email": "test@example.com", "user_timezone": "UTC"})

        # Should include both bookings (invalid one is included for safety)
        assert "Valid Meeting" in result
        assert "Invalid Meeting" in result

    @patch('cal_wrapper.api_client')
    def test_list_bookings_formatting_error(self, mock_api_client):
        """Test list_bookings with formatting error."""
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

        with patch('cal_wrapper.timezone_handler.convert_utc_to_user_timezone', side_effect=Exception("Conversion error")):
            result = list_bookings.invoke(
                {"user_email": "test@example.com", "user_timezone": "UTC"})

            # Should still include the booking with raw datetime
            assert "Test Meeting" in result
            assert "123" in result

    @patch('cal_wrapper.config')
    @patch('cal_wrapper.api_client')
    def test_get_available_slots_no_event_type_id(self, mock_api_client, mock_config):
        """Test get_available_slots when EVENT_TYPE_ID is not configured."""
        mock_config.event_type_id = None

        result = get_available_slots.invoke(
            {"date": "2025-07-25", "user_timezone": "UTC"})

        assert "Error: EVENT_TYPE_ID is not configured" in result

    @patch('cal_wrapper.api_client')
    def test_get_available_slots_api_error(self, mock_api_client):
        """Test get_available_slots with API error."""
        mock_response = ApiResponse(
            success=False,
            error="API Connection Error"
        )
        mock_api_client.get_available_slots.return_value = mock_response

        result = get_available_slots.invoke(
            {"date": "2025-07-25", "user_timezone": "UTC"})

        assert "Error fetching available slots" in result
        assert "API Connection Error" in result

    @patch('cal_wrapper.api_client')
    def test_get_available_slots_api_failure_status(self, mock_api_client):
        """Test get_available_slots when API returns failure status."""
        mock_response = ApiResponse(
            success=True,
            data={
                "status": "failure",
                "error": "No slots available"
            }
        )
        mock_api_client.get_available_slots.return_value = mock_response

        result = get_available_slots.invoke(
            {"date": "2025-07-25", "user_timezone": "UTC"})

        assert "Error: API returned failure" in result
        assert "No slots available" in result

    @patch('cal_wrapper.api_client')
    def test_get_available_slots_no_data_for_date(self, mock_api_client):
        """Test get_available_slots when no data exists for the date."""
        mock_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": {
                    "2025-07-26": []  # Different date
                }
            }
        )
        mock_api_client.get_available_slots.return_value = mock_response

        result = get_available_slots.invoke(
            {"date": "2025-07-25", "user_timezone": "UTC"})

        assert "No available slots found for 2025-07-25" in result

    @patch('cal_wrapper.api_client')
    def test_get_available_slots_empty_slots(self, mock_api_client):
        """Test get_available_slots when slots array is empty."""
        mock_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": {
                    "2025-07-25": []  # Empty slots
                }
            }
        )
        mock_api_client.get_available_slots.return_value = mock_response

        result = get_available_slots.invoke(
            {"date": "2025-07-25", "user_timezone": "UTC"})

        assert "No available slots found for 2025-07-25" in result

    @patch('cal_wrapper.api_client')
    def test_get_available_slots_formatting_error(self, mock_api_client):
        """Test get_available_slots with slot formatting error."""
        mock_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": {
                    "2025-07-25": [
                        {"start": "2025-07-25T09:00:00.000Z",
                            "end": "2025-07-25T10:00:00.000Z"}
                    ]
                }
            }
        )
        mock_api_client.get_available_slots.return_value = mock_response

        with patch('cal_wrapper.timezone_handler.convert_utc_to_user_timezone', side_effect=Exception("Conversion error")):
            result = get_available_slots.invoke(
                {"date": "2025-07-25", "user_timezone": "UTC"})

            # Should still show slots with raw datetime
            assert "Available slots for 2025-07-25" in result
            assert "2025-07-25T09:00:00.000Z" in result

    @patch('cal_wrapper.config')
    @patch('cal_wrapper.api_client')
    def test_create_booking_no_event_type_id(self, mock_api_client, mock_config):
        """Test create_booking when EVENT_TYPE_ID is not configured."""
        mock_config.event_type_id = None

        result = create_booking.invoke({
            "start_time_iso": "2025-07-25T14:00:00",
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "title": "Test Meeting",
            "user_timezone": "UTC"
        })

        assert "Error: EVENT_TYPE_ID is not configured" in result

    @patch('cal_wrapper.timezone_handler')
    def test_create_booking_invalid_time_format(self, mock_timezone_handler):
        """Test create_booking with invalid time format."""
        mock_timezone_handler.convert_iso_to_utc_api_format.side_effect = ValueError(
            "Invalid time format")

        result = create_booking.invoke({
            "start_time_iso": "invalid-datetime",
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "title": "Test Meeting",
            "user_timezone": "UTC"
        })

        assert "Invalid time format" in result

    @patch('cal_wrapper.api_client')
    def test_create_booking_api_failure_status(self, mock_api_client):
        """Test create_booking when API returns failure status."""
        mock_response = ApiResponse(
            success=True,
            data={
                "status": "failure",
                "error": "Booking conflict"
            }
        )
        mock_api_client.create_booking.return_value = mock_response

        result = create_booking.invoke({
            "start_time_iso": "2025-07-25T14:00:00",
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "title": "Test Meeting",
            "user_timezone": "UTC"
        })

        assert "Error: Booking creation failed" in result
        assert "Booking conflict" in result

    @patch('cal_wrapper.api_client')
    def test_create_booking_confirmation_formatting_error(self, mock_api_client):
        """Test create_booking with error in confirmation message formatting."""
        mock_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": {"uid": "booking123"}
            }
        )
        mock_api_client.create_booking.return_value = mock_response

        with patch('cal_wrapper.timezone_handler.convert_utc_to_user_timezone', side_effect=Exception("Conversion error")):
            result = create_booking.invoke({
                "start_time_iso": "2025-07-25T14:00:00",
                "user_name": "John Doe",
                "user_email": "john@example.com",
                "title": "Test Meeting",
                "user_timezone": "UTC"
            })

            # Should still show success with raw datetime
            assert "Success!" in result
            assert "Test Meeting" in result
            assert "booking123" in result

    @patch('cal_wrapper.api_client')
    def test_cancel_booking_api_failure_status(self, mock_api_client):
        """Test cancel_booking when bookings API returns failure status."""
        mock_response = ApiResponse(
            success=True,
            data={
                "status": "failure",
                "error": "User not found"
            }
        )
        mock_api_client.get_bookings.return_value = mock_response

        result = cancel_booking.invoke({
            "user_email": "test@example.com",
            "date": "2025-07-25",
            "time": "14:00",
            "user_timezone": "UTC"
        })

        assert "Error: Could not retrieve bookings" in result
        assert "User not found" in result

    @patch('cal_wrapper.api_client')
    @patch('cal_wrapper.booking_matcher')
    def test_cancel_booking_no_matching_booking(self, mock_booking_matcher, mock_api_client):
        """Test cancel_booking when no matching booking is found."""
        future_time = (datetime.now(pytz.UTC) + timedelta(days=1)
                       ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        mock_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": [
                    {
                        "status": "accepted",
                        "title": "Other Meeting",
                        "uid": "other123",
                        "start": future_time
                    }
                ]
            }
        )
        mock_api_client.get_bookings.return_value = mock_response
        mock_booking_matcher.find_booking_by_time.return_value = None
        mock_booking_matcher.format_booking_list.return_value = [
            "- Other Meeting: 2025-07-25 15:00 (UTC)"]

        result = cancel_booking.invoke({
            "user_email": "test@example.com",
            "date": "2025-07-25",
            "time": "14:00",
            "user_timezone": "UTC"
        })

        assert "No booking found for 2025-07-25 at 14:00" in result
        assert "Other Meeting" in result

    @patch('cal_wrapper.api_client')
    @patch('cal_wrapper.booking_matcher')
    def test_cancel_booking_no_uid(self, mock_booking_matcher, mock_api_client):
        """Test cancel_booking when matching booking has no UID."""
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
                        "start": future_time
                    }
                ]
            }
        )
        mock_api_client.get_bookings.return_value = mock_response
        mock_booking_matcher.find_booking_by_time.return_value = {
            "title": "Test Meeting",
            "start": future_time
            # No 'uid' field
        }

        result = cancel_booking.invoke({
            "user_email": "test@example.com",
            "date": "2025-07-25",
            "time": "14:00",
            "user_timezone": "UTC"
        })

        assert "Error: Booking UID not found" in result

    @patch('cal_wrapper.api_client')
    @patch('cal_wrapper.booking_matcher')
    def test_cancel_booking_cancellation_api_failure(self, mock_booking_matcher, mock_api_client):
        """Test cancel_booking when cancellation API call fails."""
        future_time = (datetime.now(pytz.UTC) + timedelta(days=1)
                       ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        # Setup get_bookings success
        get_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": [
                    {
                        "status": "accepted",
                        "title": "Test Meeting",
                        "uid": "test123",
                        "start": future_time
                    }
                ]
            }
        )

        # Setup cancel_booking failure
        cancel_response = ApiResponse(
            success=True,
            data={
                "status": "failure",
                "error": "Cannot cancel booking"
            }
        )

        mock_api_client.get_bookings.return_value = get_response
        mock_api_client.cancel_booking.return_value = cancel_response
        mock_booking_matcher.find_booking_by_time.return_value = {
            "title": "Test Meeting",
            "uid": "test123",
            "start": future_time
        }

        result = cancel_booking.invoke({
            "user_email": "test@example.com",
            "date": "2025-07-25",
            "time": "14:00",
            "user_timezone": "UTC"
        })

        assert "Error: Could not cancel the booking" in result
        assert "Cannot cancel booking" in result

    @patch('cal_wrapper.api_client')
    @patch('cal_wrapper.booking_matcher')
    def test_cancel_booking_formatting_error(self, mock_booking_matcher, mock_api_client):
        """Test cancel_booking with error in confirmation message formatting."""
        future_time = (datetime.now(pytz.UTC) + timedelta(days=1)
                       ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        # Setup successful responses
        get_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": [
                    {
                        "status": "accepted",
                        "title": "Test Meeting",
                        "uid": "test123",
                        "start": future_time
                    }
                ]
            }
        )

        cancel_response = ApiResponse(
            success=True,
            data={"status": "success"}
        )

        mock_api_client.get_bookings.return_value = get_response
        mock_api_client.cancel_booking.return_value = cancel_response
        mock_booking_matcher.find_booking_by_time.return_value = {
            "title": "Test Meeting",
            "uid": "test123",
            "start": future_time
        }

        with patch('cal_wrapper.timezone_handler.convert_utc_to_user_timezone', side_effect=Exception("Conversion error")):
            result = cancel_booking.invoke({
                "user_email": "test@example.com",
                "date": "2025-07-25",
                "time": "14:00",
                "user_timezone": "UTC"
            })

            # Should still show success with basic message
            assert "Success!" in result
            assert "Test Meeting" in result
            assert "test123" in result


class TestRescheduleBookingComprehensive:
    """Comprehensive test cases for reschedule_booking function."""

    @patch('cal_wrapper.api_client')
    def test_reschedule_booking_get_bookings_error(self, mock_api_client):
        """Test reschedule_booking when getting bookings fails."""
        mock_response = ApiResponse(
            success=False,
            error="API Connection Error"
        )
        mock_api_client.get_bookings.return_value = mock_response

        result = reschedule_booking.invoke({
            "user_email": "test@example.com",
            "current_date": "2025-07-25",
            "current_time": "14:00",
            "new_start_time_iso": "2025-07-25T16:00:00",
            "user_timezone": "UTC"
        })

        assert "Error: Could not retrieve bookings" in result

    @patch('cal_wrapper.api_client')
    @patch('cal_wrapper.booking_matcher')
    def test_reschedule_booking_invalid_new_time(self, mock_booking_matcher, mock_api_client):
        """Test reschedule_booking with invalid new time format."""
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
                        "uid": "test123",
                        "start": future_time
                    }
                ]
            }
        )
        mock_api_client.get_bookings.return_value = mock_response

        # Mock a successful booking match
        mock_booking_matcher.find_booking_by_time.return_value = {
            "title": "Test Meeting",
            "uid": "test123",
            "start": future_time
        }

        with patch('cal_wrapper.timezone_handler.convert_iso_to_utc_api_format', side_effect=ValueError("Invalid time format")):
            result = reschedule_booking.invoke({
                "user_email": "test@example.com",
                "current_date": "2025-07-25",
                "current_time": "14:00",
                "new_start_time_iso": "invalid-datetime",
                "user_timezone": "UTC"
            })

            assert "Invalid time format" in result

    @patch('cal_wrapper.api_client')
    @patch('cal_wrapper.booking_matcher')
    def test_reschedule_booking_no_matching_booking(self, mock_booking_matcher, mock_api_client):
        """Test reschedule_booking when no matching booking is found."""
        future_time = (datetime.now(pytz.UTC) + timedelta(days=1)
                       ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        mock_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": [
                    {
                        "status": "accepted",
                        "title": "Other Meeting",
                        "uid": "other123",
                        "start": future_time
                    }
                ]
            }
        )
        mock_api_client.get_bookings.return_value = mock_response
        mock_booking_matcher.find_booking_by_time.return_value = None
        mock_booking_matcher.format_booking_list.return_value = [
            "- Other Meeting: 2025-07-25 15:00 (UTC)"]

        result = reschedule_booking.invoke({
            "user_email": "test@example.com",
            "current_date": "2025-07-25",
            "current_time": "14:00",
            "new_start_time_iso": "2025-07-25T16:00:00",
            "user_timezone": "UTC"
        })

        assert "No booking found for 2025-07-25 at 14:00" in result
        assert "Other Meeting" in result

    @patch('cal_wrapper.api_client')
    @patch('cal_wrapper.booking_matcher')
    def test_reschedule_booking_reschedule_api_failure(self, mock_booking_matcher, mock_api_client):
        """Test reschedule_booking when reschedule API call fails."""
        future_time = (datetime.now(pytz.UTC) + timedelta(days=1)
                       ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        # Setup get_bookings success
        get_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": [
                    {
                        "status": "accepted",
                        "title": "Test Meeting",
                        "uid": "test123",
                        "start": future_time
                    }
                ]
            }
        )

        # Setup reschedule_booking failure
        reschedule_response = ApiResponse(
            success=True,
            data={
                "status": "failure",
                "error": "Cannot reschedule booking"
            }
        )

        mock_api_client.get_bookings.return_value = get_response
        mock_api_client.reschedule_booking.return_value = reschedule_response
        mock_booking_matcher.find_booking_by_time.return_value = {
            "title": "Test Meeting",
            "uid": "test123",
            "start": future_time
        }

        result = reschedule_booking.invoke({
            "user_email": "test@example.com",
            "current_date": "2025-07-25",
            "current_time": "14:00",
            "new_start_time_iso": "2025-07-25T16:00:00",
            "user_timezone": "UTC"
        })

        assert "Error: Reschedule failed" in result
        assert "Cannot reschedule booking" in result

    @pytest.mark.skip(reason="Debug logging interferes with mocking")
    @patch('cal_wrapper.api_client')
    @patch('cal_wrapper.booking_matcher')
    def test_reschedule_booking_formatting_error(self, mock_booking_matcher, mock_api_client):
        """Test reschedule_booking with error in confirmation message formatting."""
        future_time = (datetime.now(pytz.UTC) + timedelta(days=1)
                       ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        # Setup successful responses
        get_response = ApiResponse(
            success=True,
            data={
                "status": "success",
                "data": [
                    {
                        "status": "accepted",
                        "title": "Test Meeting",
                        "uid": "test123",
                        "start": future_time
                    }
                ]
            }
        )

        reschedule_response = ApiResponse(
            success=True,
            data={"status": "success"}
        )

        mock_api_client.get_bookings.return_value = get_response
        mock_api_client.reschedule_booking.return_value = reschedule_response
        mock_booking_matcher.find_booking_by_time.return_value = {
            "title": "Test Meeting",
            "uid": "test123",
            "start": future_time
        }

        with patch('cal_wrapper.timezone_handler.convert_utc_to_user_timezone', side_effect=Exception("Conversion error")):
            with patch('cal_wrapper.timezone_handler.convert_iso_to_utc_api_format', return_value="2025-07-25T16:00:00.000Z"):
                result = reschedule_booking.invoke({
                    "user_email": "test@example.com",
                    "current_date": "2025-07-25",
                    "current_time": "14:00",
                    "new_start_time_iso": "2025-07-25T16:00:00",
                    "user_timezone": "UTC"
                })

            # Should still show success with basic message
            assert "✅ Successfully rescheduled" in result
            assert "Test Meeting" in result
            assert "test123" in result


class TestInitializationError:
    """Test error handling during module initialization."""

    def test_config_validation_error(self):
        """Test CalApiConfig validation errors."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="CAL_API_KEY environment variable is required"):
                CalApiConfig()


if __name__ == "__main__":
    pytest.main([__file__])
