import streamlit as st
import pytchat
import pandas as pd
from multiprocessing import Process, Queue, Event
import time

# Function to extract live chat and put the data in a queue
def extract_live_chat(video_id, q, stop_signal):
    try:
        chat = pytchat.create(video_id=video_id)
        chat_data = []
        while chat.is_alive() and not stop_signal.is_set():
            for c in chat.get().sync_items():
                chat_data.append({
                    "Time": c.datetime,
                    "Author": c.author.name,
                    "Message": c.message
                })
                q.put(chat_data)  # Send data to the queue
            time.sleep(2)
    except Exception as e:
        q.put(f"Error: {str(e)}")

# Streamlit app layout
def main():
    st.title("YouTube Live Chat Dashboard")

    # Sidebar input for YouTube Video ID
    st.sidebar.header("Input YouTube Live Video ID")
    video_id = st.sidebar.text_input("Enter YouTube Video ID", "")

    # Initialize session state for storing chat data
    if "chat_data" not in st.session_state:
        st.session_state["chat_data"] = pd.DataFrame()

    # Initialize session state for managing process running status
    if "process_running" not in st.session_state:
        st.session_state["process_running"] = False

    chat_container = st.empty()  # For displaying the live chat messages
    status_container = st.empty()  # For showing running or error status

    # Button to start chat extraction
    if not st.session_state["process_running"] and st.sidebar.button("Start Extracting Live Chat"):
        if video_id:
            status_container.info("Starting live chat extraction...")

            # Create a Queue for inter-process communication
            q = Queue()

            # Create an event to handle stopping the process
            stop_signal = Event()

            # Create a separate process for extracting live chat
            process = Process(target=extract_live_chat, args=(video_id, q, stop_signal))
            process.start()
            st.session_state["process"] = process
            st.session_state["stop_signal"] = stop_signal
            st.session_state["process_running"] = True

            # Poll for data from the queue
            while process.is_alive() or not q.empty():
                if not q.empty():
                    chat_data = q.get()
                    if isinstance(chat_data, str) and chat_data.startswith("Error"):
                        status_container.error(chat_data)
                        process.terminate()
                    else:
                        df = pd.DataFrame(chat_data)
                        chat_container.dataframe(df)
                        st.session_state["chat_data"] = df

            process.join()
            status_container.success("Live chat extraction completed!")
        else:
            st.error("Please enter a valid YouTube Video ID")

    # Stop button
    if st.session_state["process_running"] and st.sidebar.button("Stop"):
        st.session_state["stop_signal"].set()
        st.session_state["process"].terminate()
        st.session_state["process_running"] = False
        status_container.success("Live chat extraction stopped!")

    # CSV download button if chat data is available
    if not st.session_state["chat_data"].empty:
        st.sidebar.markdown("### Download Chat Data")
        csv = st.session_state["chat_data"].to_csv(index=False).encode('utf-8')
        st.sidebar.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f'live_chat_{video_id}.csv',
            mime='text/csv'
        )

if __name__ == "__main__":
    main()
