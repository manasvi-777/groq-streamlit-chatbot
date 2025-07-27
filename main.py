import streamlit as st
from groq import Groq
import os
from dotenv import load_dotenv
from tools import TOOLS, TOOL_MAP
from rag_system import RAGSystem
import json
import io

# Load environment variables from .env for local development
load_dotenv()

# Streamlit page configuration
st.set_page_config(page_title="Groq Chatbot with Tools & RAG", layout="centered")

st.title("🤖 Groq-Powered Chatbot")
st.caption("🚀 A fast chatbot with calculator, currency converter, weather, and RAG!")

# Initialize Groq client and API key
try:
    groq_api_key = os.getenv("GROQ_API_KEY") or st.secrets["GROQ_API_KEY"]
except (KeyError, AttributeError):
    st.error("GROQ_API_KEY not found. Please set it in .env or Streamlit secrets.")
    st.stop()

client = Groq(api_key=groq_api_key)
GROQ_MODEL = "llama3-8b-8192"

# --- RAG System Setup ---
# Initialize session state variables for RAG
if "rag_system" not in st.session_state:
    st.session_state.rag_system = None
if "rag_documents_loaded" not in st.session_state:
    st.session_state.rag_documents_loaded = False
if "default_rag_content_loaded" not in st.session_state:
    st.session_state.default_rag_content_loaded = False

# Load default RAG document content on first run or if not loaded yet
if not st.session_state.default_rag_content_loaded:
    try:
        if os.path.exists("documents/your_knowledge_base.txt"):
            with open("documents/your_knowledge_base.txt", "r", encoding="utf-8") as f:
                default_rag_content = f.read()
            st.session_state.rag_system = RAGSystem(document_content=default_rag_content)
            st.session_state.default_rag_content_loaded = True
            st.session_state.rag_documents_loaded = True # Mark as loaded
            st.sidebar.info("Default RAG knowledge base loaded.")
        else:
            st.sidebar.warning("Default RAG knowledge base file 'documents/your_knowledge_base.txt' not found.")
    except Exception as e:
        st.sidebar.error(f"Error loading default RAG knowledge base: {e}")


st.sidebar.header("RAG Document Upload")
uploaded_file = st.sidebar.file_uploader("Upload a text file for RAG (overwrites default if uploaded)", type=["txt"])

if uploaded_file is not None:
    stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
    document_content = stringio.read()
    
    st.session_state.rag_system = RAGSystem(document_content=document_content)
    st.session_state.rag_documents_loaded = True # Mark as loaded from upload
    st.session_state.default_rag_content_loaded = False # Reset default flag as it's overwritten
    st.sidebar.success("RAG document uploaded and loaded successfully!")


# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    content_to_display = message.get("content")
    
    if message["role"] == "assistant" and message.get("tool_calls"):
        content_to_display = "*(Assistant called a tool...)*"
    elif message["role"] == "tool":
        content_to_display = f"Tool Output: {content_to_display}"
    elif content_to_display is None:
        content_to_display = ""

    with st.chat_message(message["role"]):
        st.markdown(content_to_display)


# React to user input
if prompt := st.chat_input("Ask me anything..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container immediately
    with st.chat_message("user"):
        st.markdown(prompt)


    # Prepare messages for Groq API call, including a guiding system message
    groq_messages_for_api = [{
        "role": "system",
        "content": (
            "You are a helpful and concise AI assistant. "
            "When a tool returns a result, directly state the result to the user without conversational filler, "
            "explanations about your capabilities, or how the tool works. "
            "For mathematical calculations, simply provide the numerical answer. "
            "For currency conversions, state the converted amount. "
            "For weather, state the weather information directly. "
            "For RAG questions, answer based on the provided context, stating if the answer is not in the context. "
            "When calling tools, ensure that numerical parameters like 'amount' for currency conversion are passed as numbers. "
            "Ensure that the 'expression' parameter for the 'calculate' tool is always passed as a string, even if it contains only numbers or mathematical operations."
        )
    }]

    # Manually construct messages to ensure correct properties for each role
    for m in st.session_state.messages:
        msg_dict = {"role": m["role"], "content": m["content"]}
        if m["role"] == "assistant" and m.get("tool_calls"):
            msg_dict["tool_calls"] = m["tool_calls"]
        elif m["role"] == "tool":
            msg_dict["tool_call_id"] = m["tool_call_id"]
            msg_dict["name"] = m["name"]
        groq_messages_for_api.append(msg_dict)


    # Step 1: Send user message and tools to the model
    with st.spinner("Thinking..."):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=groq_messages_for_api,
                tools=TOOLS,
                tool_choice="auto",
            )

            response_message = response.choices[0].message
            
            # --- Handle Tool Calls ---
            if response_message.tool_calls:
                st.session_state.messages.append({
                    "role": response_message.role,
                    "content": response_message.content,
                    "tool_calls": [tc.model_dump() for tc in response_message.tool_calls]
                })

                tool_outputs = []
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    if function_name in TOOL_MAP:
                        function_to_call = TOOL_MAP[function_name]
                        try:
                            tool_result = function_to_call(**function_args)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": tool_result,
                            })
                        except Exception as e:
                            error_message = f"Error executing tool {function_name}: {e}"
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": error_message,
                            })
                    else:
                        error_message = f"Tool '{function_name}' not found."
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": error_message,
                        })
                
                with st.chat_message("tool_output"):
                    for output in tool_outputs:
                        st.json({"name": output["name"], "content": output["content"]})
                
                groq_messages_for_api.extend(tool_outputs)

                second_response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=groq_messages_for_api,
                )
                assistant_response_content = second_response.choices[0].message.content
                with st.chat_message("assistant"):
                    st.markdown(assistant_response_content)
                st.session_state.messages.append({
                    "role": second_response.choices[0].message.role,
                    "content": assistant_response_content
                })

            # --- Handle No Tool Call (RAG or Direct Response) ---
            else:
                assistant_response_content = ""
                
                current_messages_for_llm = [m.copy() for m in groq_messages_for_api]

                if st.session_state.rag_system and st.session_state.rag_documents_loaded:
                    rag_prompt_content = st.session_state.rag_system.get_rag_prompt(prompt)
                    current_messages_for_llm[-1]["content"] = rag_prompt_content
                    
                    final_response = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=current_messages_for_llm,
                    )
                    assistant_response_content = final_response.choices[0].message.content
                else:
                    final_response = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=groq_messages_for_api,
                    )
                    assistant_response_content = final_response.choices[0].message.content

                with st.chat_message("assistant"):
                    st.markdown(assistant_response_content)
                st.session_state.messages.append({
                    "role": final_response.choices[0].message.role,
                    "content": assistant_response_content
                })

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.session_state.messages.append({"role": "assistant", "content": f"An error occurred: {e}"})