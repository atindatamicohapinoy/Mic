import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import os
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="GCash OCR - Gemini AI", layout="wide")
st.title("📝 GCash Form Scanner - Gemini AI")

# Setup Gemini API
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Google Sheets setup
SHEET_URL = "https://docs.google.com/spreadsheets/d/1vPKJPbIzvq3rTbIPKv4XivNtB941u9J_MH6TEmdcc10/edit"

def get_gsheet_client():
    """Connect to Google Sheets using service account"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Store mo yung service account JSON sa st.secrets as "gcp_service_account"
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client

def safe_generate_content(model_name, img, prompt):
    """Try Gemini model with fallback"""
    model = genai.GenerativeModel(model_name)
    response = model.generate_content([prompt, img])
    return response

def extract_table_gemini(image):
    """Extract table using Gemini instead of EasyOCR"""
    prompt = """
    Extract data from this GCash form into a JSON list.
    Keys: "NAME", "STORE NAME", "PHONE NUMBER", "GCASH VERIFIED ACCOUNT?".
    If there is a checkmark or "Yes", return "Yes". If empty, return "".
    Only return valid JSON array, no other text.
    Example: [{"NAME": "Juan Dela Cruz", "STORE NAME": "Sari Sari Store", "PHONE NUMBER": "09171234567", "GCASH VERIFIED ACCOUNT?": "Yes"}]
    """
    try:
        # Try Gemini 2.5 Flash first
        response = safe_generate_content("gemini-2.5-flash", image, prompt)
    except:
        # Fallback to Gemini 2.5 Flash Lite
        response = safe_generate_content("gemini-2.5-flash-lite", image, prompt)

    # Clean and parse JSON
    json_text = response.text.strip()
    if json_text.startswith("```json"):
        json_text = json_text.replace("```json", "").replace("```", "").strip()
    
    return json.loads(json_text)

uploaded_file = st.file_uploader("Upload GCash Form Photo", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ready to scan", use_column_width=True)
    
    if st.button("🔍 Run AI Scan", type="primary"):
        with st.spinner('Gemini AI is reading... ~3-5 seconds'):
            try:
                table_data = extract_table_gemini(image)
                
                if table_data:
                    st.success(f"✅ Extracted {len(table_data)} rows!")
                    df = pd.DataFrame(table_data)
                    
                    st.subheader("📋 Verify Data - Edit mo kung may mali")
                    edited_df = st.data_editor(
                        df,
                        num_rows="dynamic",
                        use_container_width=True,
                        key="editor"
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Download button
                        csv = edited_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download CSV",
                            csv,
                            "gcash_data.csv",
                            "text/csv",
                            key='download-csv',
                            use_container_width=True
                        )
                    
                    with col2:
                        # Sync to Google Sheets button
                        if st.button("🔄 SYNC to Google Sheets", use_container_width=True):
                            try:
                                with st.spinner('Syncing to Google Sheets...'):
                                    client = get_gsheet_client()
                                    sheet = client.open_by_url(SHEET_URL).sheet1
                                    
                                    # Append rows - skip header if may laman na yung sheet
                                    rows = edited_df.values.tolist()
                                    
                                    if len(sheet.get_all_values()) == 0:
                                        # Empty sheet, add headers first
                                        sheet.append_row(edited_df.columns.tolist())
                                    
                                    sheet.append_rows(rows, value_input_option='USER_ENTERED')
                                    st.success(f"✅ {len(rows)} rows synced sa Google Sheets!")
                                    st.balloons()
                                    
                            except Exception as e:
                                st.error(f"Sync failed: {str(e)}")
                                st.info("Check mo kung naka-share yung sheet sa service account email")
                else:
                    st.warning("Walang na-detect na data. Try mo mas malinaw na picture.")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.code(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
else:
    st.info("👆 Upload a GCash form photo to start")
    st.warning("⚠ REVIEW and EDIT kung may MALI")
