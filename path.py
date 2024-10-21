from dotenv import load_dotenv
import base64
import streamlit as st
import os
import io
from PIL import Image
import pdf2image
import google.generativeai as genai
import re
import time
import PyPDF2  # For extracting text from PDF
import smtplib  # For sending email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

# Configure the Gemini API key
genai.configure(api_key="AIzaSyBzB80E0C8ifzCeaW2UoX9JbV13d-e2jso")

# Define the folder where PDF files are stored
PDF_FOLDER_PATH = r"C:\Users\bsaha\OneDrive\Desktop\resumes"  # Change this to your actual folder path

# --- Helper Functions ---
def get_gemini_response(input_text, pdf_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash-002')
    try:
        response = model.generate_content([input_text, pdf_content[0], prompt])
        return response.text
    except Exception as e:
        st.error(f"Error generating response from Gemini API: {e}")
        return None

def extract_match_percentage(response_text):
    if response_text:
        match = re.search(r"(\d+)%", response_text)
        if match:
            return int(match.group(1))
    return None

def view_resume(pdf_content, filename):
    with st.expander(f"📄 View {filename}"):
        images = pdf2image.convert_from_bytes(pdf_content)
        if images:
            for image in images:
                st.image(image, use_column_width=True)

# Helper function to extract email address from the resume text
def extract_email_from_pdf(pdf_content):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        text = ""
        for page_num in range(len(reader.pages)):
            text += reader.pages[page_num].extract_text()

        # Regular expression for extracting email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            return email_match.group(0)
    except Exception as e:
        st.error(f"Error extracting email: {e}")
    return None

# Function to send email
def send_email(email, subject, message):
    sender_email = "bskoushik06@gmail.com"  # Add your email
    sender_password = "hajx jqjn hqka bssi" # Use environment variable for email password

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, msg.as_string())
        server.quit()
        st.success(f"Email successfully sent to {email}")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

# Streamlit App Configuration
st.set_page_config(page_title="Resume Ranking System", layout="wide")

# Custom CSS for aesthetics
st.markdown(
    """
    <style>
    body {
        background-color: black;
        color: white;
    }
    .stTextArea textarea, .stNumberInput input {
        background-color: black;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True
)

# Streamlit Title and Inputs
st.title("Smart Resume Matcher.")
st.subheader("Evaluate resumes against job descriptions using AI")

# Input for folder path
PDF_FOLDER_PATH = st.text_input("Enter the path to the folder containing resumes:", 
                                  value=r"C:\Users\bsaha\OneDrive\Desktop\resumes")

# Job description input
input_text = st.text_area(" Job Description:", height=150, placeholder="Enter job description here...")

# Minimum cutoff input
min_cutoff = st.number_input("Enter the minimum cutoff percentage:", min_value=0, max_value=100, value=50)

# Submission button
submit = st.button("Rank Resumes")
input_prompt = """
You are an advanced ATS scanner with expertise in data science and ATS functionality.
Your task is to evaluate each resume against the provided job description and give a 200-word justification only. 
List the match percentage.
"""

# Backend Logic for ranking resumes
if submit:
    if os.path.exists(PDF_FOLDER_PATH):
        pdf_files = [f for f in os.listdir(PDF_FOLDER_PATH) if f.endswith('.pdf')]
        
        if not pdf_files:
            st.warning("No PDF files found in the folder.")
        else:
            st.write(f"Found {len(pdf_files)} PDFs in the folder.")

            # Read PDFs and process them
            pdf_contents = [open(os.path.join(PDF_FOLDER_PATH, file), "rb").read() for file in pdf_files]

            # Show a loading spinner while processing
            with st.spinner("Processing resumes..."):
                time.sleep(0)  # Simulate processing delay
                
                resume_scores = []
                
                for idx, pdf_content in enumerate(pdf_contents):
                    prompt = input_prompt
                    response = get_gemini_response(
                        input_text, 
                        [{"mime_type": "application/pdf", "data": base64.b64encode(pdf_content).decode()}], 
                        prompt
                    )

                    if response:
                        match_percentage = extract_match_percentage(response)
                        if match_percentage is not None:
                            email = extract_email_from_pdf(pdf_content)  # Extract email
                            resume_scores.append((response, match_percentage, pdf_files[idx], pdf_content, email))
                        else:
                            st.error(f"Could not extract match percentage from the response for {pdf_files[idx]}.")
                    else:
                        st.error(f"Failed to get a valid response for {pdf_files[idx]}.")
                
                # Filter resumes based on the cutoff
                filtered_resumes = [r for r in resume_scores if r[1] >= min_cutoff]

                if filtered_resumes:
                    # Sort resumes by match percentage in descending order
                    ranked_resumes = sorted(filtered_resumes, key=lambda x: x[1], reverse=True)
                    
                    # Save the ranked resumes to session state
                    st.session_state.ranked_resumes = ranked_resumes

                    st.subheader(" Ranked Resumes")
                else:
                    st.warning("No resumes met the minimum cutoff.")
    else:
        st.error("PDF folder does not exist. Please check the folder path.")

# --- Displaying Ranked Resumes from Session State ---
if 'ranked_resumes' in st.session_state and st.session_state.ranked_resumes:
    selected_emails = []
    for idx, (response, match_percentage, filename, file, email) in enumerate(st.session_state.ranked_resumes, start=1):
        st.markdown(f"Rank {idx}: {filename} - {email if email else 'No email found'}")
        st.write(response)
        view_resume(file, filename)

        # Checkbox for selecting candidate
        if email:
            selected = st.checkbox(f"Send email to {filename}", key=f"checkbox_{idx}")
            if selected:
                selected_emails.append(email)

    # Email sending section for selected candidates
    if selected_emails:
        with st.form("bulk_email_form"):
            subject = st.text_input("Email subject for selected candidates:", value="Job Opportunity")
            message = st.text_area("Email message for selected candidates:")
            send_email_btn = st.form_submit_button("Send email to selected candidates")
            
            if send_email_btn:
                for email in selected_emails:
                    send_email(email, subject, message)
                st.success("Emails sent successfully.")
    else:   
        st.warning("No candidates selected for emailing.")