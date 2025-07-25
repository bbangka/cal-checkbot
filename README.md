# Cal.com API Wrapper with LangChain Integration

A comprehensive Flask web application that provides a chat interface for managing Cal.com bookings using LangChain and OpenAI's GPT models. This application allows users to book, reschedule, cancel meetings, and check available time slots through a conversational AI interface.

## Features

- 🤖 **AI-Powered Chat Interface**: Natural language booking management using OpenAI GPT models
- 📅 **Complete Booking Management**: Create, cancel, reschedule, and list bookings
- 🌍 **Timezone Support**: Full timezone conversion and display
- 🛠️ **LangChain Integration**: Modular tool-based architecture
- ✅ **Comprehensive Testing**: 95% test coverage with pytest
- 🔧 **Environment Configuration**: Secure API key management
- 📱 **Responsive Web UI**: Clean, modern chat interface

## Project Structure

```
liveX/
├── app.py                           # Flask web application
├── cal_wrapper.py                   # Cal.com API wrapper with LangChain tools
├── templates/
│   └── index.html                   # Chat interface frontend
├── test_cal_wrapper.py              # Unit tests
├── test_cal_wrapper_comprehensive.py # Integration tests
├── .env                             # Environment variables (not in repo)
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Prerequisites

- Python 3.8 or higher
- Cal.com account with API access
- OpenAI API key
- pip (Python package installer)

## Installation

### 1. Clone or Download the Project

```bash
# If cloning from git
git clone <repository-url>
cd liveX

# Or download and extract the project files
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install flask python-dotenv requests pytz langchain langchain-openai langchain-core
```

Or if you have a requirements.txt file:

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root directory:

```bash
touch .env
```

Add the following environment variables to your `.env` file:

```env
# Cal.com API Configuration
CAL_API_KEY=your_cal_api_key_here
CAL_EVENT_TYPE_ID=your_event_type_id_here
CAL_BASE_URL=https://api.cal.com/v2

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
```

#### How to Get Your API Keys:

**Cal.com API Key:**

1. Log into your Cal.com account
2. Go to Settings → Developer → API Keys
3. Create a new API key
4. Copy the generated key

**Cal.com Event Type ID:**

1. In Cal.com, go to Event Types
2. Select the event type you want to use
3. The ID is in the URL or can be found via the API

**OpenAI API Key:**

1. Visit [OpenAI Platform](https://platform.openai.com)
2. Sign up or log in
3. Go to API Keys section
4. Create a new secret key

## Starting the Application

### Development Server

```bash
# Make sure your virtual environment is activated
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Start the Flask development server
python app.py
```

The application will start on `http://localhost:5001`

### Production Deployment

For production deployment, consider using:

- **Gunicorn** (Linux/macOS):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

- **Waitress** (Cross-platform):

```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=5001 app:app
```

## Accessing the Application

1. **Web Interface**: Open your browser and navigate to `http://localhost:5001`
2. **Chat Interface**: Use the chat box to interact with the AI assistant
3. **API Endpoints**: The application also provides REST API endpoints

### Web Interface Usage

The chat interface supports natural language commands such as:

- "Show me my upcoming meetings"
- "Book a meeting for tomorrow at 2 PM"
- "Cancel my 3 PM meeting today"
- "What time slots are available on Friday?"
- "Reschedule my meeting from 2 PM to 4 PM"

## API Examples

### Direct API Calls

You can also make direct API calls to the chat endpoint:

#### Chat API Endpoint

**POST** `/chat`

```bash
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Show me my upcoming meetings"
      }
    ],
    "session_id": "user123"
  }'
```

#### Response Format

```json
{
  "reply": "I'd be happy to show you your upcoming meetings! To do this, I need your email address and timezone. Could you please provide:\n\n1. Your email address\n2. Your timezone (e.g., 'America/New_York', 'Europe/London', 'UTC')"
}
```

### Example Chat Conversations

#### 1. Listing Bookings

**User Input:**

```json
{
  "messages": [
    { "role": "user", "content": "Show my meetings" },
    { "role": "assistant", "content": "I need your email and timezone" },
    {
      "role": "user",
      "content": "My email is john@example.com and timezone is America/New_York"
    }
  ]
}
```

**Assistant Response:**

```
Here are your upcoming meetings:

📅 **Upcoming accepted bookings (2 found):**

🗓️ **Team Standup**
- 📧 Meeting ID: abc123
- 🕐 Time: July 25, 2025 at 09:00 AM (America/New_York)
- ⏰ Duration: 30 minutes

🗓️ **Client Review**
- 📧 Meeting ID: def456
- 🕐 Time: July 26, 2025 at 02:00 PM (America/New_York)
- ⏰ Duration: 60 minutes
```

#### 2. Booking a Meeting

**User Input:**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "I want to book a meeting for tomorrow at 2 PM"
    }
  ]
}
```

**Process:**

1. Assistant asks for name, email, meeting title, and timezone
2. Shows available time slots for the requested day
3. User confirms the specific time
4. Assistant creates the booking

#### 3. Checking Available Slots

**User Input:**

```json
{
  "messages": [
    { "role": "user", "content": "What times are available on Friday?" }
  ]
}
```

**Assistant Response:**

```
Here are the available time slots for Friday, July 25, 2025:

🕘 09:00 AM - 09:30 AM
🕙 10:00 AM - 10:30 AM
🕐 01:00 PM - 01:30 PM
🕕 06:00 PM - 06:30 PM

Please let me know which time slot you'd prefer!
```

#### 4. Canceling a Meeting

**User Input:**

```json
{
  "messages": [
    { "role": "user", "content": "Cancel my 3pm meeting today" },
    { "role": "assistant", "content": "I need your email and timezone" },
    { "role": "user", "content": "john@example.com, America/New_York" }
  ]
}
```

## LangChain Tools Available

The application includes these LangChain tools:

1. **`list_bookings`** - Retrieve user's upcoming bookings
2. **`get_available_slots`** - Check available time slots
3. **`create_booking`** - Book a new meeting
4. **`cancel_booking`** - Cancel an existing booking
5. **`reschedule_booking`** - Reschedule an existing booking

### Tool Input Schemas

Each tool has specific input requirements:

```python
# list_bookings
{
    "user_email": "user@example.com",
    "user_timezone": "America/New_York"
}

# get_available_slots
{
    "date": "2025-07-25",
    "event_type_id": "123",
    "timezone": "America/New_York"
}

# create_booking
{
    "start_time": "2025-07-25T14:00:00-04:00",
    "attendee_name": "John Doe",
    "attendee_email": "john@example.com",
    "meeting_title": "Strategy Meeting",
    "timezone": "America/New_York"
}

# cancel_booking
{
    "user_email": "user@example.com",
    "date": "2025-07-25",
    "time": "15:00",
    "timezone": "America/New_York"
}

# reschedule_booking
{
    "user_email": "user@example.com",
    "current_date": "2025-07-25",
    "current_time": "14:00",
    "new_start_time": "2025-07-25T16:00:00-04:00",
    "timezone": "America/New_York"
}
```

## Testing

The project includes comprehensive tests with 95% coverage.

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage report
pytest --cov=cal_wrapper --cov-report=html

# Run specific test file
pytest test_cal_wrapper.py

# Run specific test
pytest test_cal_wrapper.py::TestLangChainTools::test_list_bookings
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=cal_wrapper --cov-report=term-missing

# View HTML coverage report
open htmlcov/index.html
```

## Configuration

### Environment Variables

| Variable            | Required | Description                   | Example                  |
| ------------------- | -------- | ----------------------------- | ------------------------ |
| `CAL_API_KEY`       | Yes      | Your Cal.com API key          | `cal_live_xxxxx`         |
| `CAL_EVENT_TYPE_ID` | Yes      | Event type ID from Cal.com    | `123456`                 |
| `CAL_BASE_URL`      | No       | Cal.com API base URL          | `https://api.cal.com/v2` |
| `OPENAI_API_KEY`    | Yes      | OpenAI API key for GPT models | `sk-xxxxx`               |

### Timezone Support

The application supports all standard timezone formats:

- `America/New_York`
- `Europe/London`
- `Asia/Tokyo`
- `UTC`
- And all other IANA timezone identifiers

## Troubleshooting

### Common Issues

1. **"CAL_API_KEY environment variable is required"**

   - Ensure your `.env` file contains the API key
   - Check that the `.env` file is in the project root
   - Verify the environment variable name is correct

2. **"Failed to connect to Cal.com API"**

   - Verify your API key is valid
   - Check your internet connection
   - Ensure the Cal.com service is available

3. **OpenAI API errors**

   - Verify your OpenAI API key is valid
   - Check you have sufficient API credits
   - Ensure you have access to the GPT-4 model

4. **Port already in use**

   ```bash
   # Find process using port 5001
   lsof -i :5001

   # Kill the process
   kill -9 <PID>
   ```

### Debug Mode

To enable verbose logging:

```python
# In app.py, the AgentExecutor is already set to verbose=True
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,  # Shows agent's thinking process
    handle_parsing_errors=True
)
```

## Development

### Adding New Features

1. **New LangChain Tools**: Add to `cal_wrapper.py`
2. **API Endpoints**: Add to `app.py`
3. **Frontend Changes**: Modify `templates/index.html`
4. **Tests**: Add to test files

### Code Style

The project follows Python best practices:

- Type hints where applicable
- Comprehensive error handling
- Modular design with separation of concerns
- Extensive test coverage

## License

This project is for educational and development purposes. Please ensure you comply with Cal.com's API terms of service and OpenAI's usage policies.

## Support

For issues related to:

- **Cal.com API**: Check [Cal.com API Documentation](https://developer.cal.com/)
- **OpenAI API**: Check [OpenAI Documentation](https://platform.openai.com/docs)
- **LangChain**: Check [LangChain Documentation](https://docs.langchain.com/)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

---

**Happy Booking! 📅**
