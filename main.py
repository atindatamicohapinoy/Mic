import streamlit as st
import pandas as pd
from PIL import Image
import google.generativeai as genai
import json
import os

st.set_page_config(page_title="GCash OCR - Gemini AI", layout="wide")
st.title("📝 GCash Form Scanner - Gemini AI")

# Setup Gemini API
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def safe_generate_content(model_name, img, prompt):
    """Try Gemini model with fallback"""
    model = genai.GenerativeModel(model_name)
    response = model.generate_content([prompt, img])
    return response

def extract_table_gemini(image):
    """Extract table using Gemini instead of EasyOCR"""
    prompt = """
    Extract data from this GCash form into a JSON list.
    Keys: "NAME", "STORE NAME", "PHONE NUMBER", "GCASH VERIFIED ACCOUNT?", "SIGNATURE".
    If there is a checkmark or "Yes", return "Yes". If empty, return "".
    Only return valid JSON array, no other text.
    Example: [{"NAME": "Juan Dela Cruz", "STORE NAME": "Sari Sari Store", "PHONE NUMBER": "09171234567", "GCASH VERIFIED ACCOUNT?": "Yes", "SIGNATURE": ""}]
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
                        height=400
                    )
                    
                    csv = edited_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download CSV",
                        csv,
                        "gcash_form.csv",
                        "text/csv",
                        use_container_width=True
                    )
                else:
                    st.error("No table detected. Crop mo muna yung image para table lang yung kita.")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.code(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
else:
    st.info("👆 Upload a GCash form photo to start")
    st.warning("⚠️ Needs Gemini API Key - Mas accurate kaysa EasyOCR")
