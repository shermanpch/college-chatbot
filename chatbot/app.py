import asyncio
import traceback

import chainlit as cl
from dotenv import load_dotenv

from chatbot.components import vectorstore as vectorstore_component
from chatbot.components.pdf_generator import generate_pdf_report
from chatbot.workflow import main_workflow_app
from chatbot.workflow.state import create_initial_state
from projectutils.env import setup_project_environment
from projectutils.logger import setup_logger

# Load environment variables
load_dotenv(override=True)

# Setup project environment (sets working directory to project root)
setup_project_environment()

# Setup logger
logger = setup_logger(__file__)

# Global variable to hold the initialized vectorstore
db_vectorstore = None
_vectorstore_initialized = False
_initialization_lock = asyncio.Lock()  # Add thread-safe lock


async def initialize_vectorstore_globally():
    """Initialize the vectorstore once globally if not already done."""
    global db_vectorstore, _vectorstore_initialized

    # Use async lock to prevent concurrent initialization
    async with _initialization_lock:
        # Double-check pattern: check again inside the lock
        if _vectorstore_initialized:
            if db_vectorstore is not None:
                cl.user_session.set("db_vectorstore_initialized", True)
            return

        try:
            logger.info("Starting vectorstore initialization...")
            # Define rotating progress messages
            progress_messages = [
                "📚 Initializing College Database...",
                "📖 Loading university data files...",
                "🔍 Processing 1,500+ college documents...",
                "🏫 Building college information index...",
                "📊 Extracting university metadata...",
                "🔧 Setting up search infrastructure...",
                "⚡ Optimizing database performance...",
                "🎯 Preparing personalized matching...",
                "🚀 Almost ready! Finalizing setup...",
                "✨ Putting finishing touches...",
            ]

            # Send initial message
            loading_msg = await cl.Message(content=progress_messages[0]).send()

            # Create the vectorstore initialization task
            vectorstore_task = asyncio.create_task(
                vectorstore_component.get_vectorstore(
                    force_recreate=False,
                    try_create_from_source_if_missing=True,
                )
            )

            # Start the rotating message updater
            message_index = 1  # Start from second message since the first message
            update_interval = 8  # Update every 8 seconds

            while not vectorstore_task.done():
                # Wait for the update interval or until the task is done
                try:
                    await asyncio.wait_for(
                        asyncio.shield(vectorstore_task),
                        timeout=update_interval,
                    )
                    break  # Task completed
                except asyncio.TimeoutError:
                    # Task still running, update progress message
                    current_message = progress_messages[
                        message_index % len(progress_messages)
                    ]

                    # Use proper Chainlit API to update message
                    loading_msg.content = current_message
                    await loading_msg.update()

                    # Move to next message
                    message_index += 1

            # Get the result
            db_vectorstore = await vectorstore_task

            if db_vectorstore:
                stats = vectorstore_component.get_vectorstore_stats(db_vectorstore)
                doc_count = stats.get("document_count", "unknown")
                logger.info(
                    f"Global vectorstore initialized with {doc_count} documents"
                )

                # Update final success message
                loading_msg.content = (
                    f"✅ College Database ready with {doc_count} documents!"
                )
                await loading_msg.update()
                cl.user_session.set("db_vectorstore_initialized", True)
            else:  # Should not happen if get_vectorstore raises ValueError as expected
                logger.error(
                    "db_vectorstore is None after initialization attempt without error."
                )
                loading_msg.content = "⚠️ College Database could not be initialized."
                await loading_msg.update()
                cl.user_session.set("db_vectorstore_initialized", False)

        except ValueError as ve:  # Catch specific error from get_vectorstore
            logger.error(
                f"Failed to initialize global vectorstore (ValueError): {ve}",
                exc_info=True,
            )
            await cl.Message(
                content=f"⚠️ Error initializing College Database: {str(ve)}. Advanced search will be unavailable."
            ).send()
            cl.user_session.set("db_vectorstore_initialized", False)
            db_vectorstore = None
        except Exception as e:
            logger.error(
                f"Unexpected error initializing global vectorstore: {e}", exc_info=True
            )
            await cl.Message(
                content=f"❌ Unexpected error initializing College Database: {str(e)}. Some features may be unavailable."
            ).send()
            cl.user_session.set("db_vectorstore_initialized", False)
            db_vectorstore = None
        finally:
            _vectorstore_initialized = True  # Mark as attempted inside the lock


async def _send_new_assistant_messages(current_step_result, messages_before_invoke):
    """Sends new assistant messages that were added during a workflow step."""
    all_messages_from_graph_step = current_step_result.get("messages", [])

    # Get state-level flags that apply to the current step
    expected_input = current_step_result.get("expected_input")
    show_clarification_buttons = current_step_result.get(
        "show_clarification_buttons", False
    )
    show_sat_score_buttons = current_step_result.get("show_sat_score_buttons", False)

    # Collect all new assistant messages first
    new_assistant_messages = []
    for i in range(len(messages_before_invoke), len(all_messages_from_graph_step)):
        msg_data = all_messages_from_graph_step[i]
        if msg_data.get("role") == "assistant":
            assistant_content = msg_data.get("content", "")
            if assistant_content:
                new_assistant_messages.append((i, msg_data))

    # Process each message
    for msg_index, (_original_index, msg_data) in enumerate(new_assistant_messages):
        assistant_content = msg_data.get("content", "")

        # Extract message metadata (if any)
        msg_metadata = msg_data.get("metadata", {})

        # Initialize elements list, using any pre-defined elements from the graph step
        # Ensure 'elements' is a list, even if msg_data["elements"] is None or not present.
        elements = msg_data.get("elements")
        if not isinstance(
            elements, list
        ):  # Check if it's not a list (e.g. None or other type)
            elements = []  # Default to an empty list
        else:
            elements = elements[:]

        # Check if this is a college ranking message
        if msg_metadata.get("message_type") == "college_ranking":
            source_path = msg_metadata.get("source_path")
            college_name = msg_metadata.get("college_name", "College Details")

            # Add logging to track metadata processing
            logger.debug(
                f"Processing college_ranking message for {college_name}. Received source_path: '{source_path}', Full metadata: {msg_metadata}"
            )

            # Create cl.Text element with markdown content if source path exists
            if source_path:
                try:
                    # Read the markdown file content
                    with open(source_path, encoding="utf-8") as f:
                        markdown_content = f.read()

                    logger.info(
                        f"Creating cl.Text for {college_name} with markdown content ({len(markdown_content)} characters)"
                    )
                    text_element = cl.Text(
                        name=f"{college_name} Report",
                        content=markdown_content,
                        display="side",
                    )
                    elements.append(text_element)  # Append to the elements list
                except Exception as e:
                    logger.error(f"Failed to read markdown file {source_path}: {e}")
                    # Fallback: create a simple text element with error message
                    error_element = cl.Text(
                        name=f"{college_name} Report",
                        content=f"Error loading college details: {str(e)}",
                        display="side",
                    )
                    elements.append(error_element)  # Append to the elements list

        actions = []

        # Only add buttons to the LAST message when expecting user input
        is_last_message = msg_index == len(new_assistant_messages) - 1
        if is_last_message:
            # Handle clarification prompt with custom buttons
            if expected_input == "yes_no" and show_clarification_buttons:
                actions = [
                    cl.Action(
                        name="user_action",
                        label="✨ Yes - I'd love personalized questions!",
                        icon="sparkles",
                        value="yes",
                        payload={"value": "yes"},
                    ),
                    cl.Action(
                        name="user_action",
                        label="👍 No - I'm good with the current analysis",
                        icon="check",
                        value="no",
                        payload={"value": "no"},
                    ),
                ]
            # Handle SAT score prompt with custom buttons
            elif expected_input == "yes_no" and show_sat_score_buttons:
                actions = [
                    cl.Action(
                        name="user_action",
                        label="📊 Yes - Use my previous SAT score",
                        icon="chart-bar",
                        value="yes",
                        payload={"value": "yes"},
                    ),
                    cl.Action(
                        name="user_action",
                        label="✏️ No - I'll enter a different score",
                        icon="edit",
                        value="no",
                        payload={"value": "no"},
                    ),
                ]

        # Send message with elements (if any)
        await cl.Message(
            content=assistant_content,
            actions=actions or None,
            elements=elements or None,  # This will now include Plotly plots
        ).send()


@cl.action_callback("user_action")
async def on_action(action: cl.Action):
    """Handle user actions."""
    logger.info(f"Action '{action.payload}' clicked")
    # Extract the value from the payload
    action_value = action.payload.get("value", "")
    mock_message = cl.Message(content=action_value)
    await main(mock_message)


@cl.on_chat_start
async def on_chat_start():
    """Handle new chat session initialization."""
    logger.info("Starting new chat session for College Chatbot Workflow")
    await cl.Message(
        content="🎓 **Welcome to the College Chatbot!**\n\nInitializing your session, please wait..."
    ).send()

    await initialize_vectorstore_globally()

    # Small delay to ensure UI connection is stable after long initialization
    await asyncio.sleep(1)

    initial_graph_state = create_initial_state(db_vectorstore=db_vectorstore)

    try:
        logger.info("Invoking workflow for the first interaction.")
        current_step_result = await main_workflow_app.ainvoke(initial_graph_state)
        newly_added_messages_by_graph = current_step_result.get("messages", [])
        logger.info(f"Messages from workflow: {len(newly_added_messages_by_graph)}")

        if not newly_added_messages_by_graph:
            logger.warning("No messages from workflow - this is unexpected")
        else:
            logger.info("Sending messages from workflow")
            for _i, msg_data in enumerate(newly_added_messages_by_graph):
                if msg_data.get("role") == "assistant":
                    await cl.Message(content=msg_data.get("content", "")).send()

        cl.user_session.set("graph_state", current_step_result)
        logger.info("Chat session initialization completed successfully")

    except Exception as e:
        logger.error(f"Error during initial graph invocation: {e}", exc_info=True)
        error_message = f"❌ **Error initializing your session:** {str(e)}\nPlease try refreshing the page."
        await cl.Message(content=error_message).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle user messages and interact with the workflow."""
    logger.info(f"Received user query: {message.content[:100]}...")

    graph_state = cl.user_session.get("graph_state")
    if not graph_state:
        await cl.Message(
            content="Session error. Please refresh the page to start over."
        ).send()
        return

    user_input = message.content.strip().lower()

    if user_input == "exit":
        await cl.Message(
            content="👋 Goodbye! Feel free to start a new chat anytime."
        ).send()
        cl.user_session.set("graph_state", None)
        cl.user_session.set("db_vectorstore_initialized", False)
        return

    if user_input == "restart":
        await cl.Message(
            content="🚀 Restarting workflow... Please enter your SAT score."
        ).send()

        restart_state = create_initial_state(db_vectorstore=db_vectorstore)

        try:
            messages_before_restart = list(restart_state.get("messages", []))
            current_step_result = await main_workflow_app.ainvoke(restart_state)
            await _send_new_assistant_messages(
                current_step_result, messages_before_restart
            )
            cl.user_session.set("graph_state", current_step_result)
        except Exception as e:
            logger.error(f"Error during restart: {e}", exc_info=True)
            await cl.Message(content=f"❌ Error during restart: {str(e)}").send()
        return

    messages_before_invoke = list(graph_state.get("messages", []))
    graph_state["messages"].append({"role": "user", "content": message.content})
    graph_state["db_vectorstore"] = db_vectorstore

    try:
        current_step_result = await main_workflow_app.ainvoke(graph_state)
        await _send_new_assistant_messages(current_step_result, messages_before_invoke)
        cl.user_session.set("graph_state", current_step_result)

        # Generate PDF after completion messages are sent
        generate_pdf_flag = current_step_result.get("generate_pdf")

        if generate_pdf_flag:
            logger.info("Starting PDF generation process")

            # Send loading message for PDF generation
            loading_msg = await cl.Message(
                content="🔄 **Generating your PDF report...** \n\nThis may take a few moments. Please wait while we compile your personalized college recommendations."
            ).send()

            pdf_data = await generate_pdf_report(current_step_result)
            logger.info("PDF generation completed")

            # Remove the loading message
            await loading_msg.remove()

            if pdf_data:
                # Create Chainlit PDF viewer element for display
                pdf_viewer = cl.Pdf(
                    name="College Recommendation Report",
                    content=pdf_data["content"],
                    display="side",
                )

                # Create Chainlit file element for download
                report_file = cl.File(
                    name=pdf_data["filename"],
                    content=pdf_data["content"],
                    mime=pdf_data["mime"],
                )

                # Send new message with the final PDF
                await cl.Message(
                    content="📄 **Your College Recommendation Report is Ready!**",
                    elements=[pdf_viewer, report_file],
                ).send()
            else:
                # Send error message
                await cl.Message(
                    content="❌ Sorry, there was an error generating your PDF report. Please try again or contact support."
                ).send()

    except Exception as e:
        logger.error(f"Error during workflow execution: {e}", exc_info=True)
        error_traceback = traceback.format_exc()
        error_message = f"""
        ❌ **An unexpected error occurred:**

        **Error Type:** {type(e).__name__}
        **Error Message:** {str(e)}

        Please try again. If the issue persists, type 'restart' to begin a new session.

        <details><summary>Technical details</summary>
        ```
        {error_traceback}
        ```
        </details>
        """
        await cl.Message(content=error_message).send()


@cl.on_chat_resume
async def on_chat_resume(thread):
    """Handle chat resume."""
    logger.info(f"Resuming chat session for thread: {thread}")

    global db_vectorstore  # Ensure global is used
    if not cl.user_session.get("db_vectorstore_initialized", False):
        logger.warning(
            "Global vectorstore not initialized during resume, attempting initialization."
        )
        await initialize_vectorstore_globally()

    graph_state = cl.user_session.get("graph_state")
    if graph_state:
        graph_state["db_vectorstore"] = db_vectorstore
        cl.user_session.set("graph_state", graph_state)
        logger.info("Chat state restored.")
        last_messages = graph_state.get("messages", [])
        if last_messages and last_messages[-1].get("role") == "assistant":
            await cl.Message(
                content=f'Welcome back! Continuing from: "{last_messages[-1]["content"][:50]}..."'
            ).send()
        else:
            await cl.Message(
                content="Welcome back! Please continue where you left off."
            ).send()

    else:
        logger.warning(
            "Graph state not found on resume. Re-initializing chat as a new session."
        )
        await on_chat_start()
