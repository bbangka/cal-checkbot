# app_langchain.py
import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from datetime import datetime

# Import our decorated tools
from cal_wrapper import list_bookings, create_booking, get_available_slots, cancel_booking, reschedule_booking

load_dotenv()

# Initialize Flask App
app = Flask(__name__)

# 1. Define the tools the agent can use
tools = [list_bookings, create_booking,
         get_available_slots, cancel_booking, reschedule_booking]

# 2. Create the LLM model
# We use a model that supports tool calling, like gpt-4o or gpt-3.5-turbo
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# 3. Create the Prompt Template
# The prompt needs specific placeholders: 'input' for the user query
# and 'agent_scratchpad' for the agent's internal thought process.
prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a helpful assistant for booking meetings on Cal.com. "
        f"The current date is {datetime.now().isoformat()}. "
        "When a user asks to book a meeting, follow this process: "
        "1. Ask for their name, email, desired date, meeting title, and timezone "
        "2. Once you have the date and timezone, ALWAYS use get_available_slots function first with both date and timezone to show available times "
        "3. After showing available slots, ask the user to choose a specific time "
        "4. Only then call create_booking with the exact time they choose, including their timezone "
        "When a user asks to list or show bookings, you MUST ask for both their email address AND timezone "
        "before calling the list_bookings function. This ensures you show bookings with times in their preferred timezone. "
        "When a user asks to cancel a booking (e.g., 'cancel my 3pm meeting today'), follow this process: "
        "1. Ask for their email address if not provided "
        "2. Parse the date and time from their request (today = current date, convert relative dates) "
        "3. Ask for their timezone to confirm the cancellation time "
        "4. Use cancel_booking function with their email, date (YYYY-MM-DD format), time (HH:MM 24-hour format), and timezone "
        "When a user asks to reschedule a booking (e.g., 'reschedule my 2pm meeting to 4pm'), follow this process: "
        "1. Ask for their email address if not provided "
        "2. Parse the current date and time from their request "
        "3. Ask for the new desired date "
        "4. Ask for their timezone "
        "5. ALWAYS use get_available_slots function first to show available times for the new date "
        "6. After showing available slots, ask the user to choose a specific new time "
        "7. Use reschedule_booking function with their email, current date (YYYY-MM-DD), current time (HH:MM), new time (ISO format), and timezone "
        "For timezone, accept formats like 'America/New_York', 'Europe/London', 'UTC', etc."
    )),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 4. Create the Agent
# This binds the LLM, the prompt, and the tools together
agent = create_openai_tools_agent(llm, tools, prompt)

# 5. Create the Agent Executor
# This is the runtime that will actually execute the agent and tools
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,  # Set to True to see the agent's thoughts
    handle_parsing_errors=True  # Gracefully handle errors
)

# In a real app, you'd store this in a database or session
chat_history_store = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    print(f"INFO: Received data: {data}")
    messages = data.get("messages", [])

    # Get the latest user message
    if not messages or len(messages) == 0:
        return jsonify({"reply": "I didn't receive any message. Please try again."})

    # Find the last user message
    user_input = None
    for message in reversed(messages):
        if message.get("role") == "user":
            user_input = message.get("content")
            break

    if not user_input:
        return jsonify({"reply": "I didn't receive a user message. Please try again."})

    # Basic session management
    session_id = data.get("session_id", "default_session")

    # Convert messages to LangChain format for chat history (excluding the current message)
    chat_history = []
    for msg in messages[:-1]:  # Exclude the last message as it's the current input
        if msg.get("role") == "user":
            chat_history.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            chat_history.append(AIMessage(content=msg.get("content", "")))

    # The agent handles everything for us!
    response = agent_executor.invoke({
        "input": user_input,
        "chat_history": chat_history
    })

    return jsonify({"reply": response["output"]})

# You'll need to slightly update your index.html to send a session_id
# but it will work without it for a basic demo.


if __name__ == "__main__":
    app.run(debug=True, port=5001)
